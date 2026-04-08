import json
import logging
import re
from pathlib import Path
from typing import Dict, Iterable, Optional

import aiohttp
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

DATA_DIR = '/data'
STATE_FILENAME = 'blizztrack_versions.json'


def _resolve_state_file_path():
    data_path = Path(DATA_DIR) / STATE_FILENAME
    if data_path.parent.is_dir():
        return str(data_path)
    return STATE_FILENAME

# Track keys -> BlizzTrack tact codes
BLIZZTRACK_TRACKS = {
    'live': 'hero',   # Heroes of the Storm (live)
    'test': 'herot',  # Heroes of the Storm (PTR)
}

# Regions as they appear on BlizzTrack "view" pages and in the manifest API.
# HotS currently uses US/EU/CN/KR/TW/SG.
KNOWN_REGIONS = {
    'US', 'EU', 'CN', 'KR', 'TW', 'SG',
    # Legacy / other-game labels we’ve seen in older BlizzTrack scrapes.
    'NA', 'ASIA', 'LATAM', 'SEA',
}


async def run_blizztrack_healthcheck_mode():
    service = BlizztrackService()
    logging.info('Starting blizztrack standalone healthcheck mode (no Discord token required).')
    ok, versions = await service.run_healthcheck()
    logging.info('Blizztrack standalone summary: %s', ' | '.join(service.summary_lines(versions)))
    return 0 if ok else 1


class BlizztrackService:
    def __init__(self, state_file: str = None, tracks: Optional[Dict[str, str]] = None):
        self.state_file = state_file if state_file is not None else _resolve_state_file_path()
        self.tracks = tracks or BLIZZTRACK_TRACKS

    @staticmethod
    def parse_version_key(version_name):
        if not version_name:
            return ()
        numbers = re.findall(r'\d+', str(version_name))
        if numbers:
            return tuple(int(number) for number in numbers)
        return (str(version_name).lower(),)

    def find_highest_version(self, version_names: Iterable[str]):
        cleaned = [version_name for version_name in version_names if version_name]
        if not cleaned:
            return None
        return sorted(cleaned, key=self.parse_version_key)[-1]

    async def fetch_text(self, session, url):
        headers = {'User-Agent': 'ProbiusBot/1.0'}
        async with session.get(url, timeout=30, headers=headers) as response:
            if response.status != 200:
                raise RuntimeError(f'BlizzTrack request failed for {url} with status {response.status}')
            return await response.text()

    @staticmethod
    def parse_blizztrack_regions(payload):
        """Extract a {REGION: version_name} mapping from a BlizzTrack API payload.

        Current BlizzTrack manifest API shape (documented):
          /api/manifest/{tact}/versions
          {"success": true, "result": {"data": [{"region": "us", "version_name": "2.55..."}, ...]}}
        """
        region_versions: Dict[str, str] = {}

        if not isinstance(payload, dict):
            return {}

        # ✅ New/current manifest API shape
        result = payload.get('result')
        if isinstance(result, dict) and isinstance(result.get('data'), list):
            for entry in result['data']:
                if not isinstance(entry, dict):
                    continue
                region = entry.get('region') or entry.get('code')
                version_name = entry.get('version_name') or entry.get('versionName')
                if region and version_name:
                    region_versions[str(region).upper()] = str(version_name)

        # Older/alternate shapes (kept for resilience)
        if isinstance(payload.get('regions'), dict):
            for region, data in payload['regions'].items():
                if isinstance(data, dict):
                    region_versions[str(region).upper()] = data.get('name') or data.get('version') or data.get('build')

        for key in ['data', 'results', 'versions']:
            value = payload.get(key)
            if isinstance(value, list):
                for entry in value:
                    if not isinstance(entry, dict):
                        continue
                    region = entry.get('region') or entry.get('regionName') or entry.get('code')
                    version_name = (
                        entry.get('version_name')
                        or entry.get('versionName')
                        or entry.get('name')
                        or entry.get('version')
                        or entry.get('build')
                    )
                    if region and version_name:
                        region_versions[str(region).upper()] = str(version_name)

        return {region: version for region, version in region_versions.items() if version}

    async def fetch_track_versions(self, session, track_key):
        tact = self.tracks[track_key]

        # BlizzTrack’s current documented API for versions manifests.
        # Docs: GET /api/manifest/{tact}/versions (optional ?seqn=...)
        api_urls = [
            f'https://blizztrack.com/api/manifest/{tact}/versions',
            # Back-compat attempts (older scrapers used these; keep just in case)
            f'https://blizztrack.com/api/{tact}?type=versions',
            f'https://blizztrack.com/api/{tact}/versions',
        ]

        api_failures = []
        for url in api_urls:
            try:
                text = await self.fetch_text(session, url)
                payload = json.loads(text)
                region_versions = self.parse_blizztrack_regions(payload)
                if region_versions:
                    LOGGER.debug('Blizztrack API response found for %s via %s', track_key, url)
                    return region_versions
            except Exception as exc:
                api_failures.append(f'{url} -> {exc}')

        if api_failures:
            LOGGER.warning(
                'Blizztrack API attempts failed for %s (%s tries). First failure: %s',
                track_key,
                len(api_failures),
                api_failures[0],
            )

        # HTML fallback (works even if API changes/breaks)
        html_urls = [
            f'https://blizztrack.com/view/{tact}?type=versions',
            f'https://blizztrack.com/view/{tact}/versions',
        ]
        html = None
        html_failures = []
        for url in html_urls:
            try:
                html = await self.fetch_text(session, url)
                LOGGER.info('Blizztrack HTML fallback used for %s via %s', track_key, url)
                break
            except Exception as exc:
                html_failures.append(f'{url} -> {exc}')

        if html is None:
            if html_failures:
                LOGGER.warning(
                    'Blizztrack HTML fallback attempts failed for %s (%s tries). First failure: %s',
                    track_key,
                    len(html_failures),
                    html_failures[0],
                )
            LOGGER.warning('No Blizztrack data available for track %s', track_key)
            return {}

        soup = BeautifulSoup(html, 'html.parser')

        # BlizzTrack "view" pages are list/section based.
        # Parse the "Current Data" section and pick the first version-looking token
        # after each region code.
        text = soup.get_text('\n', strip=True)
        if 'Current Data' in text:
            text = text.split('Current Data', 1)[1]
        if 'Previous Data' in text:
            text = text.split('Previous Data', 1)[0]

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        region_versions = {}
        version_re = re.compile(r'^\d+(?:\.\d+){2,6}$')

        for i, line in enumerate(lines):
            region = line.upper()
            if region not in KNOWN_REGIONS:
                continue

            # Search forward a bit for a version string.
            for j in range(i + 1, min(i + 25, len(lines))):
                candidate = lines[j]
                if version_re.match(candidate):
                    region_versions[region] = candidate
                    break

        if not region_versions:
            LOGGER.warning('Blizztrack HTML parse produced no regions for %s', track_key)
        return region_versions

    async def get_versions(self):
        async with aiohttp.ClientSession() as session:
            results = {}
            for track_key in self.tracks:
                region_versions = await self.fetch_track_versions(session, track_key)
                results[track_key] = {
                    'regions': region_versions,
                    'current': self.find_highest_version(region_versions.values()) or 'unknown',
                }
            return results

    def read_version_state(self):
        try:
            with open(self.state_file, 'r', encoding='utf-8') as version_file:
                return json.load(version_file)
        except Exception as exc:
            LOGGER.info('No existing blizztrack state file (%s): %s', self.state_file, exc)
            return {}

    def write_version_state(self, state):
        with open(self.state_file, 'w', encoding='utf-8') as version_file:
            json.dump(state, version_file, indent=2, sort_keys=True)

    def summary_lines(self, current_versions):
        lines = []
        for track_key in self.tracks:
            track_data = current_versions.get(track_key, {}) if isinstance(current_versions, dict) else {}
            current_version = track_data.get('current', 'unknown') if isinstance(track_data, dict) else 'unknown'
            region_versions = track_data.get('regions', {}) if isinstance(track_data, dict) else {}
            regions = ', '.join([f"{region}: {version}" for region, version in sorted(region_versions.items())]) if region_versions else 'none found'
            lines.append(f"{track_key}: {current_version} ({regions})")
        return lines

    async def run_healthcheck(self):
        versions = await self.get_versions()
        if not versions:
            LOGGER.error('Blizztrack healthcheck failed: no versions returned.')
            return False, versions

        all_known = True
        for track_key, data in versions.items():
            current = data.get('current', 'unknown')
            region_count = len(data.get('regions', {})) if isinstance(data, dict) else 0
            LOGGER.info('Blizztrack healthcheck track=%s current=%s regions=%s', track_key, current, region_count)
            if current == 'unknown' or region_count == 0:
                all_known = False

        if all_known:
            LOGGER.info('Blizztrack healthcheck passed.')
        else:
            LOGGER.warning('Blizztrack healthcheck warning: partial or unknown version data.')
        return all_known, versions
