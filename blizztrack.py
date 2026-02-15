import argparse
import asyncio
import json
import logging
import re
from typing import Dict, Iterable, Optional

import aiohttp
from bs4 import BeautifulSoup

BLIZZTRACK_VERSION_STATE_FILE = 'blizztrack_versions.json'
BLIZZTRACK_TRACKS = {
    'live': 'hero',
    'test': 'herot',
}
KNOWN_REGIONS = {'EU', 'NA', 'KR', 'CN', 'ASIA', 'LATAM', 'SEA'}

logger = logging.getLogger(__name__)


def parse_version_key(version_name):
    if not version_name:
        return ()
    numbers = re.findall(r'\d+', str(version_name))
    if numbers:
        return tuple(int(number) for number in numbers)
    return (str(version_name).lower(),)


def find_highest_version(version_names: Iterable[str]) -> Optional[str]:
    cleaned = [version_name for version_name in version_names if version_name]
    if not cleaned:
        return None
    return sorted(cleaned, key=parse_version_key)[-1]


class BlizztrackMonitor:
    def __init__(self, state_file=BLIZZTRACK_VERSION_STATE_FILE):
        self.state_file = state_file
        self.state = self.read_state()
        self.last_fetch_errors = {}

    async def fetch_text(self, session, url):
        headers = {'User-Agent': 'ProbiusBot/1.0'}
        logger.debug('Requesting BlizzTrack URL: %s', url)
        async with session.get(url, timeout=30, headers=headers) as response:
            if response.status != 200:
                raise RuntimeError(f'BlizzTrack request failed for {url} with status {response.status}')
            return await response.text()

    def parse_regions(self, payload):
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
        view_name = BLIZZTRACK_TRACKS[track_key]
        errors = []
        api_urls = [
            f'https://blizztrack.com/api/{view_name}?type=versions',
            f'https://blizztrack.com/api/v1/{view_name}?type=versions',
            f'https://blizztrack.com/api/view/{view_name}?type=versions',
            f'https://blizztrack.com/api/{view_name}/versions',
            f'https://blizztrack.com/api/v1/{view_name}/versions',
        ]
        for url in api_urls:
            try:
                text = await self.fetch_text(session, url)
                payload = json.loads(text)
                region_versions = self.parse_regions(payload)
                if region_versions:
                    logger.info('Fetched %s versions from API endpoint %s', track_key, url)
                    self.last_fetch_errors[track_key] = []
                    return region_versions
            except Exception as exc:
                errors.append(f'{url}: {exc}')
                logger.debug('Failed API endpoint %s for %s: %s', url, track_key, exc)

        html_urls = [
            f'https://blizztrack.com/view/{view_name}?type=versions',
            f'https://blizztrack.com/view/{view_name}/versions',
        ]
        html = None
        for url in html_urls:
            try:
                html = await self.fetch_text(session, url)
                logger.info('Using HTML fallback endpoint %s for %s', url, track_key)
                break
            except Exception as exc:
                errors.append(f'{url}: {exc}')
                logger.debug('Failed HTML endpoint %s for %s: %s', url, track_key, exc)
        if html is None:
            self.last_fetch_errors[track_key] = errors
            logger.warning('Unable to fetch any endpoint for %s. Errors: %s', track_key, ' | '.join(errors[-3:]))
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
        self.last_fetch_errors[track_key] = errors
        return region_versions

    async def get_versions(self):
        async with aiohttp.ClientSession() as session:
            results = {}
            for track_key in BLIZZTRACK_TRACKS:
                region_versions = await self.fetch_track_versions(session, track_key)
                results[track_key] = {
                    'regions': region_versions,
                    'current': find_highest_version(region_versions.values()) or 'unknown'
                }
            return results

    def read_state(self):
        try:
            with open(self.state_file, 'r', encoding='utf-8') as version_file:
                return json.load(version_file)
        except Exception:
            return {}

    def write_state(self, state):
        with open(self.state_file, 'w', encoding='utf-8') as version_file:
            json.dump(state, version_file, indent=2, sort_keys=True)

    def summary_lines(self, versions: Dict):
        lines = []
        for track_key in BLIZZTRACK_TRACKS:
            track_data = versions.get(track_key, {}) if isinstance(versions, dict) else {}
            current_version = track_data.get('current', 'unknown') if isinstance(track_data, dict) else 'unknown'
            region_versions = track_data.get('regions', {}) if isinstance(track_data, dict) else {}
            regions = ', '.join([f"{region}: {version}" for region, version in sorted(region_versions.items())]) if region_versions else 'none found'
            lines.append(f"{track_key}: {current_version} ({regions})")
        return lines

    def validate_versions(self, versions):
        checks = []
        for track_key in BLIZZTRACK_TRACKS:
            track_data = versions.get(track_key, {}) if isinstance(versions, dict) else {}
            regions = track_data.get('regions', {}) if isinstance(track_data, dict) else {}
            current = track_data.get('current', 'unknown') if isinstance(track_data, dict) else 'unknown'
            checks.append((f'{track_key}_regions_present', bool(regions)))
            checks.append((f'{track_key}_current_known', current != 'unknown'))
        return checks

    async def run_healthcheck(self):
        versions = await self.get_versions()
        checks = self.validate_versions(versions)
        ok = all(result for _, result in checks)
        return ok, versions, checks, self.last_fetch_errors


async def _run_cli(log_level):
    logging.basicConfig(level=log_level, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    monitor = BlizztrackMonitor()
    ok, versions, checks, fetch_errors = await monitor.run_healthcheck()

    print('BlizzTrack healthcheck summary:')
    for line in monitor.summary_lines(versions):
        print(f'  - {line}')

    print('Checks:')
    for name, passed in checks:
        symbol = 'OK' if passed else 'FAIL'
        print(f'  - {name}: {symbol}')

    if any(fetch_errors.values()):
        print('Recent fetch errors:')
        for track_key, errors in fetch_errors.items():
            if not errors:
                continue
            print(f'  - {track_key}:')
            for err in errors[-3:]:
                print(f'      * {err}')

    if ok:
        print('Result: BlizzTrack appears to be working.')
        return 0

    print('Result: BlizzTrack checks failed (see FAIL entries above).')
    return 1


def main():
    parser = argparse.ArgumentParser(description='BlizzTrack healthcheck (no Discord token required)')
    parser.add_argument('--debug', action='store_true', help='Enable verbose debug logging')
    args = parser.parse_args()
    log_level = logging.DEBUG if args.debug else logging.INFO
    raise SystemExit(asyncio.run(_run_cli(log_level)))


if __name__ == '__main__':
    main()
