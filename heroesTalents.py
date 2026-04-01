from printFunctions import *
from urllib.request import urlopen
from aliases import *
from itertools import repeat
from json import loads
import asyncio
import aiohttp
import nest_asyncio
import re
import html as htmlmod
from bs4 import BeautifulSoup
import os
from pathlib import Path

nest_asyncio.apply()


def trimForHeroesTalents(hero):
	hero = hero.replace('The', '').lower()
	remove = ".' -_"
	for i in remove:
		hero = hero.replace(i, '')
	hero = hero.replace('butcher', 'thebutcher').replace('ú', 'u').replace('cho', 'chogall')
	return hero


async def additionalInfo(hero, name, description):
	addDict = {  # Adds text to the end of descriptions
		'alexstrasza': {
			'Cleansing Flame': 'Dragonqueen: Cleansing Flame is cast instantly. The duration of Dragonqueen is paused, while basic abilities continue to cool down while in flight.',
			'Dragon Scales': 'Getting Stunned, Rooted, or Silenced while Dragon Scales is active refreshes its duration to 2 seconds.',
			'Life-Binder': 'Dragonqueen: The cast range of Life-Binder is increased from 6 to 9.'
		},
		'anubarak': {'Cocoon': 'Each instance of damage reduces the remaining duration by 0.5 seconds.'},
		'chen': {'Storm, Earth, Fire': 'Using Storm, Earth, Fire removes most negative effects from Chen.'},
		'falstad': {'Epic Mount': 'The arrival marker becomes invisible to enemies.'},
		'garrosh': {'Armor Up': 'Stacks with other sources of armour, up to 75.'},
		'guldan': {
			'Life Tap': 'Costs 222 (+4% per level) Health.',
			'Ruinous Affliction': 'This third strike is also considered to be the first strike of the next three hits.'
		},
		'imperius': {'Impaling Light': 'The damage bonus is per brand and stacks to 225%'},
		'johanna': {"Heaven's Fury": 'Up to two healing and two damaging bolts per second.'},
		'kelthuzad': {'The Damned Return': 'Does not interact with Arcane Echoes, Phylactery, or Hungering Cold.'},
		'lunara': {'Leaping Strike': 'Lunara is unstoppable while leaping.'},
		'maiev': {'Spirit of Vengeance': 'Reactivate to teleport to the spirit.'},
		'malfurion': {
			'Moonfire': 'The area itself stays revealed for 2 seconds.',
			'Celestial Alignment': 'Also extends the reveal of located area to 5 seconds.'
		},
		'mei': {'Avalanche': 'Damage is not affected by number of consumed heroes.'},
		'mephisto': {'Spite': 'Also extends mana regeneration from the healing globe.'},
		'muradin': {'Grand Slam': 'If an ally participates in the takedown, a second charge is gained'},
		'orphea': {'Overflowing Chaos': 'The damage bonus is multiplicative.'},
		'rehgar': {"Farseer's Blessing": 'Both casts heal around the target.'},
		'sylvanas': {
			'Haunting Wave': 'Sylvanas is unstoppable while flying to the banshee. Reactivation becomes available 0.5 seconds after first E.',
			'Mercenary Queen': 'Mercenaries will not be stunned if the third application is through Remorseless.',
			'Black Arrows': 'Remorseless shots do not disable enemies.',
			'Remorseless': "This shot originates from Sylvanas' target, and does not disable buildings while Black Arrows is active. If the third stack on the secondary target is reached through this shot, the target will not be affected by Mercenary Queen."
		},
		'tassadar': {
			'Psychic Shock': 'Psionic Storm deals 2 additional ticks of damage.',
			'Shock Ray': '0.375 second wind up before beam starts, additional 0.75 second channel while beam is moving. If the channel is interrupted, beam instantly disappears.'
		},
		'tracer': {'Ricochet': 'Ricochet shots interact with Telefrag, but not Focus Fire.'},
		'tychus': {'Focusing Diodes': 'The damage bonus is multiplicative.'},
		'tyrande': {"Huntress' Fury": "Splashes give cooldown reduction on Light of Elune, but do not trigger any of Tyrande's other Basic Attack related effects."},
		'valla': {
			'Strafe': 'The duration of Hatred is paused when channeling, and reset to full when Strafe ends.',
			'Vault': 'The damage bonus is multiplicative.'
		},
		'zarya': {'Energy': 'The damage bonus is multiplicative.'}
	}
	if hero in addDict:
		if name in addDict[hero]:
			description += ' ***' + addDict[hero][name] + '***'
	return description


async def fixTooltips(hero, name, description):
	fixDict = {  # Replaces text using strikethrough
		'anubarak': {'Nerubian Armor': ['ed', ' ']},
		'auriel': {"Swift Sweep": ['50%', '100%']},
		'blaze': {"Suppressive Fire": ['Power', 'Damage']},
		'cassia': {'War Traveler': ['8%', '4%', '1 second', '0.5 seconds']},
		'guldan': {'Ruinous Affliction': ['strike deals', "strike's damage is increased to"]},
		'malfurion': {"Nature's Balance": ['area', 'radius']},
		'lili': {'Healing Brew': ['ally (prioritizing Heroes)', 'allied Hero']},
		'ragnaros': {'Blistering Attacks': ['Basic Abilities', 'Living Meteor or Blast Wave, or enemy heroes with Empower Sulfuras,']},
		'sylvanas': {'Haunting Wave': ['teleport', 'fly']},
		'tracer': {
			'Sleight of Hand': ['20%', '24%'],
			'Reload': ['0.75', '0.8125']
		},
		'varian': {'Victory Rush': ['or Monster dies', 'dies, or when you kill a Monster']},
		'zuljin': {'Boneslicer': ["is no longer removed by", 'lasts for 30']}
	}
	if hero in fixDict:
		if name in fixDict[hero]:
			for i in range(len(fixDict[hero][name]) // 2):
				description = description.replace(
					fixDict[hero][name][2 * i],
					'~~' + fixDict[hero][name][2 * i] + '~~ ' + '***' + fixDict[hero][name][2 * i + 1] + '***'
				)
	return await additionalInfo(hero, name, description)


async def descriptionFortmatting(description):
	if 'Repeatable Quest' in description:
		description = description.replace('Repeatable Quest:', '\n    **❢ Repeatable Quest:**')
	else:
		description = description.replace('Quest:', '\n    **❢ Quest:**')
	description = description.replace('Reward:', '\n    **? Reward:**').replace('Gambit:', '\n   **♙Gambit:**').replace('Passive:', '\n    **Passive:**')
	return description


async def fetch(session, url):
	async with session.get(url) as response:
		return await response.text()


async def downloadHero(hero, client, patch):
	with _open_heroes_data_file(hero, is_test=False) as page:
		page = loads(page.read())
		abilities = []
		if hero in ['ltmorales', 'valeera', 'deathwing', 'zarya']:
			resource = 'energy'
		elif hero == 'chen':
			resource = 'brew'
		elif hero == 'sonya':
			resource = 'fury'
		elif hero == 'gazlowe':
			resource = 'scrap'
		else:
			resource = 'mana'

		for i in page['abilities'].keys():
			for ability in page['abilities'][i]:
				if 'hotkey' in ability:
					output = '**[' + ability['hotkey'] + '] '
				else:
					output = '**[D] '
				output += ability['name'] + ':** '
				if 'cooldown' in ability or 'manaCost' in ability:
					output += '*'
					if 'cooldown' in ability:
						output += str(ability['cooldown']) + ' seconds'
						if 'manaCost' in ability:
							output += ', '
					if 'manaCost' in ability:
						output += str(ability['manaCost']) + ' ' + resource
					output += ';* '
				output += await descriptionFortmatting(ability['description'])
				output = await fixTooltips(hero, ability['name'], output)
				abilities.append(output)
		if hero == 'samuro':
			abilities.append("**[D] Image Transmission:** *14 seconds;* Activate to switch places with a target Mirror Image, removing most negative effects from Samuro and the Mirror Image.\n**Advancing Strikes:** Basic Attacks against enemy Heroes increase Samuro's Movement Speed by 25% for 2 seconds.")
		elif hero == 'hogger':
			abilities.append("**[D] Rage:** Rage is gained by taking damage or dealing Basic Attack damage. Hogger’s Basic Ability cooldowns refresh 1% faster for every 2 points of Rage. After 3 seconds of not gaining Rage, it begins to quickly decay. ***Hogger gains 5 Rage when landing a Basic Attack and 1 Rage each time he takes damage.***")

		talents = []
		keys = sorted(list(page['talents'].keys()), key=lambda x: int(x))
		for key in keys:
			tier = page['talents'][key]
			talentTier = []
			for talent in tier:
				output = '**[' + str(int(key) - 2 * int(hero == 'chromie' and key != '1')) + '] '
				output += talent['name'] + ':** '
				if 'cooldown' in talent:
					output += '*' + str(talent['cooldown']) + ' seconds;* '
				output += await descriptionFortmatting(talent['description'])
				output = await fixTooltips(hero, talent['name'], output)
				talentTier.append(output)
			talents.append(talentTier)
		client.heroPages[aliases(hero)] = (abilities, talents)


async def loopFunction(client, heroes, patch):
	for future in asyncio.as_completed(map(downloadHero, heroes, repeat(client), repeat(patch))):
		await future


async def downloadAll(client, argv):
	if len(argv) == 2:
		patch = argv[1]
	else:
		patch = ''
	heroes = getHeroes()
	heroes = list(map(trimForHeroesTalents, heroes))
	loop = asyncio.get_event_loop()  # running instead of event when calling from a coroutine.
	loop.run_until_complete(loopFunction(client, heroes, patch))


# -------------------------
# Fandom stats (updated)
# -------------------------

def _norm_key(s: str) -> str:
	return " ".join(s.replace("\xa0", " ").strip().lower().split())


async def _fetch_fandom_data_vars(session: aiohttp.ClientSession, hero: str) -> dict:
	"""
	Returns dict like {"health": "2450", "attack speed": "1.25", ...}
	by calling the MediaWiki API parse endpoint for Data:<hero>.
	This avoids Fandom UI endpoints that commonly return 403.
	"""
	api_url = "https://heroesofthestorm.fandom.com/api.php"
	params = {
		"action": "parse",
		"page": f"Data:{hero}",
		"prop": "text",
		"format": "json",
		"formatversion": "2",
		"redirects": "1",
	}

	async with session.get(api_url, params=params) as resp:
		resp.raise_for_status()
		data = await resp.json(content_type=None)

	html_text = data.get("parse", {}).get("text", "")
	if not html_text:
		return {}

	soup = BeautifulSoup(html_text, "html.parser")

	# Data pages usually have a wikitable with 3 columns: Parameter | Variable | Value
	table = soup.select_one("table.wikitable") or soup.find("table")
	if not table:
		return {}

	out = {}
	for tr in table.find_all("tr"):
		cells = tr.find_all(["td", "th"])
		if len(cells) < 3:
			continue

		var = _norm_key(cells[1].get_text(" ", strip=True))
		val = cells[2].get_text(" ", strip=True)
		val = htmlmod.unescape(val).replace("\xa0", " ").strip()

		# Skip header row if present
		if var and var != "variable":
			out[var] = val

	return out


async def heroStats(hero, channel, allowRecursion=True):
	async with channel.typing():
		if hero == 'The_Lost_Vikings':
			for i in ['Olaf', 'Baleog', 'Erik']:
				await heroStats(i, channel)
			return
		elif hero == 'Rexxar' and allowRecursion:
			for i in ['Rexxar', 'Misha']:
				await heroStats(i, channel, False)  # :spaghetti:
			return
		elif hero == 'Gall':
			await heroStats('Cho', channel)
			return

		usefulStats = [
			'date',
			'health',
			'resource',
			'resource type',
			'attack speed',
			'attack range',
			'attack damage',
			'unit radius'
		]

		headers = {
			# Fandom tends to prefer "real" UA strings.
			"User-Agent": "HotS-Stats-Bot/1.0 (+discord; aiohttp)",
			"Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
			"Accept-Language": "en-US,en;q=0.9",
		}

		timeout = aiohttp.ClientTimeout(total=20)

		try:
			async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
				vars_map = await _fetch_fandom_data_vars(session, hero)

			if not vars_map:
				await channel.send(f'``{hero}:`` Could not find stat data.')
				return

			# Make resource nicer if type is present
			if 'resource' in vars_map and 'resource type' in vars_map:
				vars_map['resource'] = f"{vars_map['resource']} {vars_map['resource type']}".strip()

			output = []
			for k in usefulStats:
				if k not in vars_map:
					continue
				label = (k.replace('attack', 'aa')
						   .replace('unit ', '')
						   .replace('health', 'hp')
						   .capitalize())
				output.append('**' + label + '**: ' + vars_map[k])

			if output:
				await channel.send('``' + hero + ':`` ' + ', '.join(output))
			else:
				await channel.send(f'``{hero}:`` Could not find stat data.')

		except Exception as e:
			await channel.send(f'``{hero}:`` Stat fetch failed: {type(e).__name__}: {e}')

def _open_heroes_data_file(hero, is_test=False):
	volume_folder = '/heroes-talents-test' if is_test else '/heroes-talents'
	bundled_folder = 'heroes-talents-test' if is_test else 'heroes-talents'
	filename = f'{hero}.json'

	# Check if volume is mounted
	volume_path = Path(volume_folder) / filename
	if volume_path.exists():
		return open(volume_path, 'r')

	# Fall back to bundled folder
	bundled_path = Path(bundled_folder) / filename
	if bundled_path.exists():
		return open(bundled_path, 'r')

	raise FileNotFoundError(f'{filename} not found in {volume_folder} or {bundled_folder}')


def _resolve_data_path(filename, is_test=False):
	volume_folder = '/heroes-talents-test' if is_test else '/heroes-talents'
	bundled_folder = 'heroes-talents-test' if is_test else 'heroes-talents'

	# Check if volume is mounted
	volume_path = Path(volume_folder) / filename
	if volume_path.exists():
		return str(volume_path)

	# Fall back to bundled folder
	bundled_path = Path(bundled_folder) / filename
	if bundled_path.exists():
		return str(bundled_path)

	return None


def readVersion(filename):
	is_test = 'test' in filename
	resolved_path = _resolve_data_path(filename, is_test=is_test)

	if resolved_path:
		try:
			with open(resolved_path, 'r', encoding='utf-8') as f:
				return f.read().strip()
		except Exception:
			return ''
	return ''


def parseVersion(v):
	try:
		return tuple(int(x) for x in v.split('.'))
	except:
		return (0,)


async def downloadHeroTest(hero, client, patch):
	try:
		with _open_heroes_data_file(hero, is_test=True) as page:
			page = loads(page.read())
			abilities = []
			if hero in ['ltmorales', 'valeera', 'deathwing', 'zarya']:
				resource = 'energy'
			elif hero == 'chen':
				resource = 'brew'
			elif hero == 'sonya':
				resource = 'fury'
			elif hero == 'gazlowe':
				resource = 'scrap'
			else:
				resource = 'mana'

			for i in page['abilities'].keys():
				for ability in page['abilities'][i]:
					if 'hotkey' in ability:
						output = '**[' + ability['hotkey'] + '] '
					else:
						output = '**[D] '
					output += ability['name'] + ':** '
					if 'cooldown' in ability or 'manaCost' in ability:
						output += '*'
						if 'cooldown' in ability:
							output += str(ability['cooldown']) + ' seconds'
							if 'manaCost' in ability:
								output += ', '
						if 'manaCost' in ability:
							output += str(ability['manaCost']) + ' ' + resource
						output += ';* '
					output += await descriptionFortmatting(ability['description'])
					output = await fixTooltips(hero, ability['name'], output)
					abilities.append(output)
			if hero == 'samuro':
				abilities.append("**[D] Image Transmission:** *14 seconds;* Activate to switch places with a target Mirror Image, removing most negative effects from Samuro and the Mirror Image.\n**Advancing Strikes:** Basic Attacks against enemy Heroes increase Samuro's Movement Speed by 25% for 2 seconds.")
			elif hero == 'hogger':
				abilities.append("**[D] Rage:** Rage is gained by taking damage or dealing Basic Attack damage. Hogger's Basic Ability cooldowns refresh 1% faster for every 2 points of Rage. After 3 seconds of not gaining Rage, it begins to quickly decay. ***Hogger gains 5 Rage when landing a Basic Attack and 1 Rage each time he takes damage.***")

			talents = []
			keys = sorted(list(page['talents'].keys()), key=lambda x: int(x))
			for key in keys:
				tier = page['talents'][key]
				talentTier = []
				for talent in tier:
					output = '**[' + str(int(key) - 2 * int(hero == 'chromie' and key != '1')) + '] '
					output += talent['name'] + ':** '
					if 'cooldown' in talent:
						output += '*' + str(talent['cooldown']) + ' seconds;* '
					output += await descriptionFortmatting(talent['description'])
					output = await fixTooltips(hero, talent['name'], output)
					talentTier.append(output)
				talents.append(talentTier)
			client.heroPages_test[aliases(hero)] = (abilities, talents)
	except FileNotFoundError:
		pass


async def loopFunctionTest(client, heroes, patch):
	for future in asyncio.as_completed(map(downloadHeroTest, heroes, repeat(client), repeat(patch))):
		await future


async def downloadAllTest(client, argv):
	patch = argv[1] if len(argv) == 2 else ''
	heroes = list(map(trimForHeroesTalents, getHeroes()))
	loop = asyncio.get_event_loop()
	loop.run_until_complete(loopFunctionTest(client, heroes, patch))