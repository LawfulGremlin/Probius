import json
import logging
import re
from typing import Dict, Iterable, Optional

import aiohttp
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

BLIZZTRACK_TRACKS = {
    'live': 'hero',
    'test': 'herot',
}

KNOWN_REGIONS = {'EU', 'NA', 'KR', 'CN', 'ASIA', 'LATAM', 'SEA'}


class BlizztrackService:
    def __init__(self, state_file: str = 'blizztrack_versions.json', tracks: Optional[Dict[str, str]] = None):
        self.state_file = state_file
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
        region_versions = {}
        if isinstance(payload, dict):
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
                        version_name = entry.get('name') or entry.get('version') or entry.get('build')
                        if region and version_name:
                            region_versions[str(region).upper()] = version_name
        return {region: version for region, version in region_versions.items() if version}

    async def fetch_track_versions(self, session, track_key):
        view_name = self.tracks[track_key]
        api_urls = [
            f'https://blizztrack.com/api/{view_name}?type=versions',
            f'https://blizztrack.com/api/v1/{view_name}?type=versions',
            f'https://blizztrack.com/api/view/{view_name}?type=versions',
            f'https://blizztrack.com/api/{view_name}/versions',
            f'https://blizztrack.com/api/v1/{view_name}/versions',
        ]

        api_failures = []
        for url in api_urls:
            try:
                text = await self.fetch_text(session, url)
                payload = json.loads(text)
                region_versions = self.parse_blizztrack_regions(payload)
                if region_versions:
                    LOGGER.info('Blizztrack API response found for %s via %s', track_key, url)
                    return region_versions
            except Exception as exc:
                api_failures.append(f'{url} -> {exc}')

        if api_failures:
            LOGGER.warning('Blizztrack API attempts failed for %s (%s tries). First failure: %s', track_key, len(api_failures), api_failures[0])

        html_urls = [
            f'https://blizztrack.com/view/{view_name}?type=versions',
            f'https://blizztrack.com/view/{view_name}/versions',
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
                LOGGER.warning('Blizztrack HTML fallback attempts failed for %s (%s tries). First failure: %s', track_key, len(html_failures), html_failures[0])
            LOGGER.warning('No Blizztrack data available for track %s', track_key)
            return {}

        soup = BeautifulSoup(html, 'html.parser')
        region_versions = {}
        for row in soup.find_all('tr'):
            columns = [column.get_text(strip=True) for column in row.find_all(['td', 'th'])]
            if len(columns) < 2:
                continue
            for index in range(len(columns) - 1):
                region = columns[index].upper()
                version_name = columns[index + 1]
                if region in KNOWN_REGIONS and version_name:
                    region_versions[region] = version_name

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
