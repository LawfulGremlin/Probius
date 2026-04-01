#A HotS Discord bot
#Call in Discord with [hero/modifier]
#Modifier is hotkey or talent tier
#Data is pulled from HotS wiki
#Project started on 14/9-2019

import asyncio
import io
import re
import random
import discord
import time
from sys import argv#Where to get the JSONs
from discord.ext import tasks
from discord.ext import commands

from aliases import *			#Spellcheck and alternate names for heroes
from printFunctions import *	#The functions that output the things to print
from heroesTalents import *		#The function that imports the hero pages
from emojis import *			#Emojis
from miscFunctions import*		#Edge cases and help message
from getProbiusToken import *	#The token is in an untracked file because this is a public Github repo
from talentComparison import *	#Live vs PTR talent diffing
from windstriders import *		#Wind Striders server-specific features

import os
def getProbiusToken():
	"""Return the Discord bot token.
	Supports two sources, in priority order:
	  1. DISCORD_TOKEN env var pointing to a Docker secrets file path
		 (e.g. /run/secrets/probius_token) — file contents are read and returned.
	  2. DISCORD_TOKEN env var containing the token value directly.
	Falls back to the original getProbiusToken() from the imported module if
	DISCORD_TOKEN is not set at all.
	"""
	token = os.environ.get("DISCORD_TOKEN", "")
	if not token:
		# Fall back to the original implementation from getProbiusToken.py
		import getProbiusToken as _gpt
		return _gpt.getProbiusToken()
	if os.path.isfile(token):
		with open(token) as f:
			return f.read().strip()
	return token
from builds import *			#Hero builds
from rotation import *			#Weekly rotation
from quotes import *			#Lock-in quotes
from draft import *
from reddit import *
from sorting import *
from patchNotes import *
from lfg import *
from maps import *
from discordIDs import *
from blizztrack import BlizztrackService
#from imageColour import *

import logging
logging.basicConfig(level=logging.INFO)

botChannels={'Wind Striders':DiscordChannelIDs['WS.Probius']}

drafts={}#Outside of client so it doesn't reset on periodic restarts or [restart]
lastDraftMessageDict={}
draftNames={}

buildsAliases=['guide','build','b','g','builds','guides']
quotesAliases=['quote','q','quotes']
rotationAlises=['rotation','rot','sale','sales']
aliasesAliases=['aliases','acronyms']
wikipageAliases=['page','wiki']
randomAliases=['random','ra','rand']
draftAliases=['draft','d','phantomdraft','pd','mockdraft','md']
colourAliases=['colour','colours','c','colors','color']
heroStatsAliases=['stats','info']
emojiAliases=['emoji','emojis','emote','emotes']
coinsAliases=['coin','flip','coinflip','cf']
redditAliases=['reddit','re']
helpAliases=['help','info']
talentAliases=['talent','talents','t']#don't remove t, talentAliases is used for [X/q,t]
rollAliases=['roll','dice']
patchNotesAliases=['patchnotes','patch','pn','pa']
deleteAliases=['delete','deletemessages','deletemessage']
lfgAlises=['lfg','find']
listAliases=['list','waitlist','wl']
mapImageAliases=['map','m','battleground','bg']
restartAliases=['restart','shutdown','stop']
confidenceAliases=['ci','confidence','confidenceinterval']
heroAliases=['hero', 'heroes', 'bruiser', 'healer', 'support', 'ranged', 'melee', 'assassin', 'mage', 'marksman', 'tank', 'marksmen']
coachingAliases=['coach', 'coaching', 'coachingsession']
randomBuildAliases=['randombuild','rb','randb','randbuild','randomb']
versionAliases=['version']

SUPPRESS_USER_IDS = [#It can generally be assumed that suppression is not active.
	DiscordUserIDs['Probius'],  # Probius
#	786255199069143101,  # GuineaPig
]

blizztrack_service=BlizztrackService()
def read_probius_version() -> str:
	from heroesTalents import _resolve_data_path
	try:
		resolved_path = _resolve_data_path('.hversion', is_test=False)
		if not resolved_path:
			return "unknown (.hversion missing)"
		with open(resolved_path, 'r', encoding='utf-8') as f:
			v = f.read().strip()
			return v or "unknown (empty .hversion)"
	except Exception as e:
		return f"unknown (error reading .hversion: {e})"

async def mainProbius(client,message,texts):
	global exitBool
	for draftAlias in draftAliases: #Don't want to log draft commands because they really spam.
		if 'new' in message.content.lower():continue
		if '['+draftAlias+'/' in message.content.lower():
			break
	else:#The elusive for else control flow
		guildname=message.channel.guild.name
		guildname='Nexus school' if guildname=='Nexus Schoolhouse' else guildname#Nexus Schoolhouse is too long 
		guildname='Schuifpui' if guildname=='De Schuifpui Schavuiten' else guildname
		channelName=message.channel.name
		channelName='hots' if channelName=='heroes-got-canceled' else channelName
		loggingMessage=f"{guildname}, {channelName}, {message.author.name}#{message.author.discriminator} ({message.author.id}) issued command {message.content}"
		print(loggingMessage)

	for text in texts:
		command=text[0].replace(' ','')
		if command in ['trait','r','w','e','passive','react','...']:#Do nothing
			continue
		if command in ['scaling']:
			await message.channel.send('https://cdn.discordapp.com/attachments/741762417976934460/906568639304585247/unknown.png')
			continue
		if command in ['time','t']:
			await countdown(message,text)
			continue
		if command in randomBuildAliases and len(text)==2:
			await randomBuild(client, message.channel, aliases(text[1]))
			continue
		if command in coachingAliases:
			await coaching(message)
			return
		if command in ['avatarcolour','avatarcolor']:
			#Hogs CPU resources
			#await avatarColour(client,message.channel,text[1])
			continue
		if command in ['event','season']:
			await event(message.channel)
			continue
		if command in ['armor','armour','ehp']:
			await message.channel.send('https://cdn.discordapp.com/attachments/741762417976934460/801905601809612821/unknown.png')
			continue
		if command=='hoggerangles':
			await message.channel.send('https://editor.p5js.org/Asddsa76/sketches/CmGYMS2j1')
			continue
		if command in ['schedule','patchschedule']:
			await schedule(message)
			continue
		if command =='sortlist':
			if message.guild.get_role(DiscordRoleIDs['WS.Olympian']) not in message.author.roles:#Not mod
				await message.channel.send(message.author.mention+' <:bonk:761981366744121354>')
			else:
				await sortList(message)
			continue
		if command in ['name', 'names','n']:
			names=[(i.nick or i.name)+(' ('+i.name+')')*int(bool(i.nick)) for i in message.guild.members if text[1].lower() in i.name.lower() or i.nick and text[1].lower() in i.nick.lower()]
			await message.channel.send('\n'.join(names)+'\n'+str(len(names))+' '+text[1].capitalize()+'s')
			continue
		if command in heroAliases+[i+'s' for i in heroAliases]:
			await heroes(message,text,message.channel,client)
			continue
		if command=='ping':
			await ping(message.channel)
			continue
		if command=='membercount':
			await memberCount(message.channel)
			continue
		if command in versionAliases:
			with open('.hversion', 'r', encoding='utf-8') as version_file:
				version = version_file.read().strip()
			blizztrack_versions = await blizztrack_service.get_versions()
			if blizztrack_versions is None:
				live_version='unknown'
				test_version='unknown'
			else:
				live_version=blizztrack_versions.get('live',{}).get('current','unknown')
				test_version=blizztrack_versions.get('test',{}).get('current','unknown')
			await message.channel.send(
				'Current live version: '+live_version+'\n'
				+'Current test version: '+test_version+'\n'
				+'Probius is version: '+version
			)
			continue
		if command in confidenceAliases:
			await confidence(message.channel,text)
			continue
		if command=='exit' and message.author.id==DiscordUserIDs['Asddsa']:
			exitBool=1
			await client.close()
		if command in restartAliases:
			exitBool=0
			await client.logout()
		if command in mapImageAliases:
			await mapImage(message.channel,text[1])
			continue
		if command=='core':
			await coreAbilities(message.channel,await mapAliases(text[1]))
			continue
		if command in listAliases:
			await waitList(message,text,client)
			continue
		if command in lfgAlises:
			await lfg(message.channel,text[1],client)
			continue
		if command in deleteAliases:
			await deleteMessages(message.author,text[1],client)
			continue
		if command in patchNotesAliases:
			await patchNotes(message.channel,text)
			continue
		if command in talentAliases:
			await message.channel.send("Call a hero's talent tier with [hero/level]")
			continue
		if command in rollAliases:
			await roll(text,message)
			continue
		if command=='sort':
			await sortFromMessage(text[1],message,client)
			continue
		if command==':disapproval':
			await message.channel.send('ಠ_ಠ')
			continue
		if command in [':summon','summon']:
			if len(text)==1:
				await message.channel.send('༼ つ ◕\\_◕ ༽つ')
			elif '@' in text[1]:
				await message.channel.send('{0} {0} Summon {1}! {0} {0}'.format('༼ つ ◕\\_◕ ༽つ', message.author.mention))
			else:
				await message.channel.send('{0} {0} Summon {1}! {0} {0}'.format('༼ つ ◕\\_◕ ༽つ', message.content.split('[')[1].split('/')[1].split(']')[0]))#text[1] is all lowercase etc.
			continue
		if command in colourAliases:
			await message.channel.send(file=discord.File('WS colours.png'))
			continue
		if message.author.id==DiscordUserIDs['Asddsa'] or message.author.id==DiscordUserIDs['MindHawk'] or message.author.id==DiscordUserIDs['medimold']:
			if command=='serverchannels':
				await message.channel.send([channel.name for channel in message.channel.guild.channels])
				continue
			if command=='repeat' and len(text)==2:
				await message.channel.send(message.content.split('[')[1].split('/')[1].split(']')[0])#text[1] is all lowercase
				await message.delete()
				continue
		if command== 'unsorted' and message.channel.guild.name=='Wind Striders':
			await ws_command_unsorted(message, client)
			continue
		if command=='byprobiusbepurged' and message.channel.guild.name=='Wind Striders':
			await ws_command_byprobiusbepurged(message, client)
			continue
		if command == 'vote':
			await vote(message,text)
			continue
		if command in coinsAliases:
			await message.channel.send(random.choice(['Heads','Tails']))
			continue
		if command in redditAliases:
			await reddit(client,message,text)
			continue
		if command in ['avatar','a']:
			await message.channel.send(await getAvatar(client,message.channel,text[1]))
			continue
		if command=='':#Empty string. Aliases returns Abathur when given this.
			continue
		if command in draftAliases:
			await draft(drafts,message.channel,message.author,text,lastDraftMessageDict,draftNames)
			continue
		if command in randomAliases:
			if len(text)==1:
				await message.channel.send(getQuote(random.choice(getHeroes())))
				continue
			command=random.choice(getHeroes())
		if command in helpAliases:
			if len(text)==2 and command in heroStatsAliases:#[info/hero]
				await heroStats(aliases(text[1]),message.channel)
			else:
				await message.channel.send(helpMessage())
			continue
		if command in buildsAliases:
			if len(text)==2:
				if message.channel.guild.id==DiscordGuildIDs['WindStriders'] and message.channel.id!=DiscordChannelIDs['WS.Probius'] and message.content[0]=='[':#In WS, not in #probius, first character is [
					if message.guild.get_role(DiscordRoleIDs['WS.CoreMember']) not in message.author.roles:#Not core member
						await wrongChannelBuild(message)
						await guide(aliases(text[1]),message.guild.get_channel(DiscordChannelIDs['WS.Probius']))
						continue
				await guide(aliases(text[1]),message.channel)
			else:
				await message.channel.send("Elitesparkle's builds: <https://elitesparkle.wixsite.com/hots-builds>")
			continue
		if command in rotationAlises:
			await rotation(message.channel)
			continue
		if command=='goodbot':
			await emoji(client,['Probius','love'],message.channel)
			continue
		if command=='badbot':
			if message.author.id in ProbiusPrivilegesIDs:
				await emoji(client,['Probius','sad'],message.channel)
			else:
				await emoji(client,[':pylonbat'],message.channel)
			continue
		if ':' in command:
			await emoji(client,text,message.channel,message)
			continue
		if ']' in command:
			continue
		if command in ['chogall',"cho'gall",'cg','cho gall','cho-gall']:
			await message.channel.send("Cho and Gall are 2 different heroes. Choose one of them")
			print('Dual hero')
			continue
		if command in quotesAliases:
			if len(text)==2:
				await message.channel.send(getQuote(aliases(text[1])))
			elif text[0]!='q':#Calling [q] alone shouldn't show link, but [q/hero] works, as well as [quotes]
				await message.channel.send('All hero select quotes: <https://github.com/Asddsa76/Probius/blob/master/quotes.txt>')
			continue
		if command in aliasesAliases:
			await message.channel.send('All hero alternate names: <https://github.com/Asddsa76/Probius/blob/master/aliases.py>')
			continue
		if command == 'all':
			await printAll(client,message,text[1],True)
			continue
		if command in emojiAliases:
			await message.channel.send('Emojis: [:hero/emotion], where emotion is of the following: happy, lol, sad, silly, meh, angry, cool, oops, love, or wow.')
			continue
		try:
			if len(text)==1 and command[0]=='t' and command[8] ==',':#[t3221323,sam]
				await printCompactBuild(client,message.channel,command)
				continue
			if len(text)==2 and command[0]=='t' and len(command)==8 and command!='tassadar':#[t3221323/sam]
				await printCompactBuild(client,message.channel,','.join(text))
				continue
		except:pass
		#From here it's actual heroes, or a search
		hero=command
		if len(hero)==1 or (len(hero)==2 and ('1' in hero or '2' in hero)):#Patch notes have abilities in []. Don't want spammed triggers again. Numbers for R1, R2, etc.
			continue
		hero=aliases(hero)
		if len(text)==2:#If user switches to hero first, then build/quote
			if text[1] in buildsAliases:
				if message.channel.guild.id==DiscordGuildIDs['WindStriders'] and message.channel.id!=DiscordChannelIDs['WS.Probius']:#In WS, not in #probius
					if message.guild.get_role(DiscordRoleIDs['WS.CoreMember']) not in message.author.roles:#Not core member
						await wrongChannelBuild(message)
						await guide(hero,message.guild.get_channel(DiscordChannelIDs['WS.Probius']))
						continue
				await guide(hero,message.channel)
				continue
			if text[1] in quotesAliases and text[1]!='q':
				await message.channel.send(getQuote(hero))
				continue
			if text[1] in heroStatsAliases:
				await heroStats(hero,message.channel)
				continue
		try:
			(abilities,talents)=client.heroPages[hero]
		except:
			try:#If no results, then "hero" isn't a hero
				await printAll(client,message,text[0])
			except:
				pass
			continue
		
		output=''
		try:
			tier=text[1]#If there is no identifier, then it throws exception
			if tier in randomAliases:
				await message.channel.send(printTier(talents,random.randint(0,6)))
				continue
			if tier in randomBuildAliases:
				await randomBuild(client, message.channel, hero)
				continue
		except:
			quote=getQuote(hero)
			output='\n'.join(abilities)
			await printLarge(message.channel,quote+output)
			await heroStats(hero,message.channel)
			continue
		if output=='':
			if ',' in tier and any(i in tier for i in talentAliases):
				await printAbilityTalents(message,abilities,talents,tier.split(',')[0],hero)
				continue
			if tier.isdigit():
				tier = int(tier)
				tier_index = int(tier/3) + int(hero=='Chromie' and tier not in [1,18])
				output = printTier(talents, tier_index)  # live default

				live_v = readVersion('.hversion')
				test_v = readVersion('.hversion-test')
				if test_v and live_v and parseVersion(test_v) > parseVersion(live_v) and hero in client.heroPages_test:
					try:
						(_, test_talents) = client.heroPages_test[hero]
						live_block, ptr_block = diffTierWithMoves(talents, test_talents, tier_index)
						if ptr_block.strip() and ptr_block != live_block:
							output = (
								f"**Live [{live_v}]**\n{live_block}\n\n"
								f"**PTR [{test_v}]**\n{ptr_block}"
							)
					except:
						pass
				tier=tier_index#Keep tier as index for rest of flow
			elif tier in ['mount','z']:
				await message.channel.send(printAbility(abilities,'z'))
				continue
			elif tier=='extra':
				await message.channel.send(printAbility(abilities,'1'))
				continue
			elif tier=='r':#Ultimate
				if hero=='Tracer':#She starts with her heroic already unlocked, and only has 1 heroic
					output=abilities[3]
				else:
					output=printTier(talents,3-2*int(hero=='Varian'))#Varian's heroics are at lvl 4
					if hero=='Deathwing':
						output=abilities[3]+'\n'+output#Deathwing has Cataclysm baseline
				live_v=readVersion('.hversion')
				test_v=readVersion('.hversion-test')
				if test_v and live_v and parseVersion(test_v) > parseVersion(live_v) and hero in client.heroPages_test:
					try:
						(test_abilities,test_talents)=client.heroPages_test[hero]
						if hero=='Tracer':
							test_output=test_abilities[3]
						else:
							test_output=printTier(test_talents,3-2*int(hero=='Varian'))
							if hero=='Deathwing':
								test_output=test_abilities[3]+'\n'+test_output
						if test_output != output:
							live_block, ptr_block = diffHeroicOutput(output, test_output)
							output = (
								f"**Live [{live_v}]**\n{live_block}\n\n"
								f"**PTR [{test_v}]**\n{ptr_block}"
							)
					except:
						pass
			elif len(tier)==1 and tier in 'dqwe':#Ability (dqwe)
				output=printAbility(abilities,tier)
				live_v=readVersion('.hversion')
				test_v=readVersion('.hversion-test')
				if test_v and live_v and parseVersion(test_v) > parseVersion(live_v) and hero in client.heroPages_test:
					try:
						(test_abilities,_)=client.heroPages_test[hero]
						test_output=printAbility(test_abilities,tier)
						if test_output != output:
							live_diff, ptr_diff = diffAbilityOutput(output, test_output)
							output = (
								f"**Live [{live_v}]**\n{live_diff}\n\n"
								f"**PTR [{test_v}]**\n{ptr_diff}"
							)
					except:
						pass
			elif tier == 'trait':
				output = printAbility(abilities, 'd')
				live_v = readVersion('.hversion')
				test_v = readVersion('.hversion-test')
				if test_v and live_v and parseVersion(test_v) > parseVersion(live_v) and hero in client.heroPages_test:
					try:
						(test_abilities, _) = client.heroPages_test[hero]
						test_output = printAbility(test_abilities, 'd')
						if test_output != output:
							live_diff, ptr_diff = diffAbilityOutput(output, test_output)
							output = (
								f"**Live [{live_v}]**\n{live_diff}\n\n"
								f"**PTR [{test_v}]**\n{ptr_diff}"
							)

					except:
						pass
			elif tier =='all':
				await printEverything(client,message,abilities,talents)
				return
			elif tier in wikipageAliases:#Linking user to wiki instead of printing everything
				await message.channel.send('<https://heroesofthestorm.gamepedia.com/Data:'+hero+'#Skills>')
				continue
			else:
				output = await printSearch(abilities, talents, tier, hero, True)
				if output and hero in client.heroPages_test:
					live_v = readVersion('.hversion')
					test_v = readVersion('.hversion-test')
					if test_v and live_v and parseVersion(test_v) > parseVersion(live_v):
						try:
							(test_abilities, test_talents) = client.heroPages_test[hero]
							test_output = await printSearch(test_abilities, test_talents, tier, hero, True)
							if test_output != output:
								live_block, ptr_block = diffSearchOutput(
									output, test_output,
									abilities, talents,
									test_abilities, test_talents
								)
								output = (
									f"**Live [{live_v}]**\n{live_block}\n\n"
									f"**PTR [{test_v}]**\n{ptr_block}"
								)
						except:
							pass

		if len(output)==2:#If len is 2, then it's an array with output split in half
			if message.channel.name=='rage':
				await message.channel.send(output[0].upper())
				await message.channel.send(output[1].upper())
			else:
				await message.channel.send(output[0])
				await message.channel.send(output[1])
		else:
			if message.channel.name=='rage':
				output=output.upper()
			try:
				await message.channel.send(output)
			except:
				if output=='':
					try:#If no results, it's probably an emoji with : forgotten. Prefer to call with : to avoid loading abilities and talents page
						await emoji(client,[hero,tier],message.channel)
						continue
					except:
						pass
					if message.channel.name=='rage':
						await message.channel.send('ERROR: {} DOES NOT HAVE "{}".'.format(hero,tier).upper())
					else:
						await message.channel.send('Error: {} does not have "{}".'.format(hero,tier))
					print('No results')
				else:
					if message.channel.name=='rage':
						await printLarge(message.channel,output.upper())
					else:
						await printLarge(message.channel,output)

def findTexts(message):
	allTexts=[]
	wholeText=message.content.lower()
	for text in wholeText.split('\n'):
		if not text or '>' == text[0]:#This line is a quote
			continue
		leftBrackets=[1+m.start() for m in re.finditer(r'\[',text)]#Must escape brackets when using regex
		rightBrackets=[m.start() for m in re.finditer(r'\]',text)]
		texts=[text[leftBrackets[i]:rightBrackets[i]].split('/') for i in range(len(rightBrackets))]
		if len(leftBrackets)>len(rightBrackets):#One extra unclosed at end
			texts.append(text[leftBrackets[-1]:].split('/'))
		allTexts+=texts
	return allTexts

class MyClient(discord.Client):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.seenTitles=[]
		self.seenPosts=[]
		self.forwardedPosts=[]
		self.proxyEmojis={}
		# create the background task and run it in the background
		self.bgTask0 = self.loop.create_task(self.bgTaskSubredditForwarding())
		self.bgTask1 = self.loop.create_task(self.bgTaskBlizztrackVersionCheck())

		self.heroPages={}
		self.heroPages_test={}
		self.lastWelcomeImage=[]
		self.waitList=[]
		self.ready=False#Wait until ready before taking commands

		#Region:region lfg
		self.wsLfgRoles={
		DiscordRoleIDs['WS.RegionEU']:DiscordRoleIDs['WS.LfgEU'],
		DiscordRoleIDs['WS.RegionNA']:DiscordRoleIDs['WS.LfgNA'],
		DiscordRoleIDs['WS.RegionAsia']:DiscordRoleIDs['WS.LfgAsia'],
		DiscordRoleIDs['WS.RegionCN']:DiscordRoleIDs['WS.LfgCN'],
		DiscordRoleIDs['WS.RegionLatAM']:DiscordRoleIDs['WS.LfgLatAM'],
		DiscordRoleIDs['WS.RegionSEA']:DiscordRoleIDs['WS.LfgSEA']}
		self.rulesChannel=None
		self.welcomeMessage=''
		self.botChannels=botChannels
		self.blizztrackVersionState=blizztrack_service.read_version_state()
		self.blizztrackAnnouncedVersions={}  # {track_key: set of version strings already role-pinged}

	async def should_suppress_actions(self):
		for guild in self.guilds:
			for user_id in SUPPRESS_USER_IDS:
				member = guild.get_member(user_id)
				if member and str(member.status) in ("online", "idle", "dnd"):
					return True
		return False
		
	async def log_to_console(self, text: str) -> None:
		print(text)

	def blizztrack_summary_lines(self,current_versions):
		return blizztrack_service.summary_lines(current_versions)

	async def suppression_status_loop(self):
		"""Background task to update bot status based on suppression state."""
		last_state = None
		await self.wait_until_ready()
		while not self.is_closed():
			suppressed = await self.should_suppress_actions()
			if suppressed != last_state:
				if suppressed:
					await self.change_presence(status=discord.Status.dnd)
					print("Suppression active: Bot set to idle.")
				else:
					await self.change_presence(status=discord.Status.online)
					print("Suppression inactive: Bot set to online.")
				last_state = suppressed
			await asyncio.sleep(15)  # check every 15 seconds, or longer if you prefer

	async def on_ready(self):
		print('Logged on...')
		self.loop.create_task(self.suppression_status_loop())
		print('Downloading heroes...')
		await downloadAll(self,argv)
		await downloadAllTest(self,argv)
#		print('Fetching proxy emojis...')
#		guild = client.get_guild(603924426769170433)
#		if guild is None:
#			print("WARNING: Guild with ID 603924426769170433 not found. Skipping emoji proxy setup.")
#			self.proxyEmojis = {}
#		else:
#			self.proxyEmojis = await getProxyEmojis(guild)
		print('Filling up with Reddit posts...')
		self.forwardedPosts=[]
		self.seenTitles=await fillPreviousPostTitles(self)#Fills seenTitles with all current titles
		await prime_recent_discord_reddit_ids(self)
		print("Bot is in these guilds:")
		for g in client.guilds:
			print(f"{g.name} ({g.id})")
		self.ready=True
		await self.check_blizztrack_versions(announce_if_first_run=True)
		logging.info("Probius running version: %s", read_probius_version())
		print('Ready!')
		await ws_on_ready(self)

	async def on_message(self, message):
		print(f"{message.channel.guild}, {message.channel.name}, {message.author.name}#{message.author.discriminator} ({message.author.id}) wrote: {message.content}")
		## Repeat command for Probius (moldy) - Not suppressed
		if '[' in message.content:
			for txt in findTexts(message):
				command = txt[0].replace(' ', '')
				if command == 'mepeat' and len(txt) == 2:
					# Repeat the message, then optionally delete the original (like [repeat])
					await message.channel.send(message.content.split('[')[1].split('/')[1].split(']')[0])
					await message.delete()
					return
		if await self.should_suppress_actions():
			return
		await super().on_message(message) if hasattr(super(), "on_message") else None
		await ws_on_message(message, self)
		pingNames={'medimold':DiscordUserIDs['medimold'],'libraries':DiscordUserIDs['libraries'], 'twinkles':DiscordUserIDs['twinkles']}
		pingList=[pingNames[i] for i in pingNames.keys() if '@'+i in message.content.replace(' ','').lower()]
		if pingList:
			await message.channel.send(' '.join(['<@'+str(i)+'>' for i in pingList]))
		if message.author.id==DiscordUserIDs['Gooey']:
			if 'explod' in message.content.lower():
				await message.add_reaction('<:explodes:955458830244913153>')
			if 'a'==message.content.lower():
				await message.add_reaction("🅰")
		if message.author.bot:#Don't respond to bots
			return
		if 'baelog' in message.content.lower():
			if message.channel.guild.id==DiscordGuildIDs['WindStriders']:await client.get_channel(DiscordChannelIDs['WS.Probius']).send(message.author.mention+'Ba**LE**og\nhttps://i.imgur.com/Nrcg11Z.png')
			else:await message.channel.send('Ba**LE**og\nhttps://i.imgur.com/Nrcg11Z.png')
		if self.ready==False:
			return
		elif '[' in message.content:
			texts=findTexts(message)
			await mainProbius(self,message,texts)
		await removeEmbeds(message)
		if message.author.id==0:#Birthday cake
			await message.add_reaction('🍰')
		
	async def on_message_edit(self, before, after):
		if await self.should_suppress_actions():
			return
		await super().on_message_edit(before, after) if hasattr(super(), "on_message_edit") else None
		await ws_on_message_edit(before, after, self)
		if before.author.bot:
			return
		if '[' in after.content:
			try:
				beforeTexts=findTexts(before)
			except:
				beforeTexts=[]
			newTexts=[i for i in findTexts(after) if i not in beforeTexts]
			if newTexts:
				await mainProbius(self,after,newTexts)

		await removeEmbeds(after)
		if '<@' in after.content:
			newMentions=[i for i in findMentions(after) if i not in findMentions(before)]
			if newMentions:
			# 	await after.channel.send(', '.join(newMentions)+', '+after.author.name+' wants to ping you!')
				message=await after.channel.send(after.author.mention+" editing pings into messages won't ping the person.\nIf you want their attention, you'll have to ping them in a new message!")
				await asyncio.sleep(10)
				await message.delete()

	async def on_raw_reaction_add(self, payload):
		if await self.should_suppress_actions():
			return
		await super().on_raw_reaction_add(payload) if hasattr(super(), "on_raw_reaction_add") else None
		member = payload.member or self.get_user(payload.user_id)
		if member is None:
			try:
				member = await self.fetch_user(payload.user_id)
			except:
				return
		if self.user and member.id==self.user.id:#Probius did reaction
			return
		try:
			channel = self.get_channel(payload.channel_id)
			if channel is None:
				channel = await self.fetch_channel(payload.channel_id)
			message=await channel.fetch_message(payload.message_id)
		except:
			return
		if message.author.id==DiscordUserIDs['AdvisorBot']:#Advisor wrote message
			return
		if await ws_on_reaction_add(payload, message, member, self):
			return
		if self.user and message.author.id==self.user.id:#Message is from Probius
			if str(payload.emoji)=='👎':#downvoted with thumbs down
				if await ws_check_reddit_downvote(message, member, self):
					return
				elif 'reddit.com' in message.content:
					return
				elif '<:bonk:761981366744121354>' in message.content or '@' in message.content:
					return
				output=member.name+' deleted a message from Probius'
				await self.log_to_console(output)
				await message.delete()
				return

			elif str(payload.emoji)=='👍' and message.reactions[[i.emoji for i in message.reactions].index(str(payload.emoji))].me:
				if 'Talent build' in message.content:
					await message.remove_reaction(payload.emoji,message.author)
					await printBuildFromReaction(client,message)
					output=member.name+' viewed talents'
					await self.log_to_console(output)
					return

		if member.id in ProbiusPrivilegesIDs:#Reaction copying
			await message.add_reaction(payload.emoji)

	async def on_raw_reaction_remove(self, payload):
		if await self.should_suppress_actions():
			return
		await super().on_raw_reaction_remove(payload) if hasattr(super(), "on_raw_reaction_remove") else None
		member=client.get_user(payload.user_id)
		try:
			message=await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
		except:
			return
		await ws_on_reaction_remove(payload, message, member, self)

	async def on_member_join(self,member):
		if await self.should_suppress_actions():
			return
		await super().on_member_join(member) if hasattr(super(), "on_member_join") else None
		if member.guild.name=='Wind Striders':
			await ws_on_member_join(member, self)

	async def on_member_remove(self,member):
		if await self.should_suppress_actions():
			return
		await super().on_member_remove(member) if hasattr(super(), "on_member_remove") else None
		if member.guild.name=='Wind Striders':
			await ws_on_member_remove(member, self)
			
	async def on_member_update(self,before,after):
		if await self.should_suppress_actions():
			return
		await super().on_member_update(before, after) if hasattr(super(), "on_member_update") else None
		if after.guild.id==DiscordGuildIDs['WindStriders']:
			await ws_on_member_update(before, after, self)
				
	async def bgTaskSubredditForwarding(self):
		await self.wait_until_ready()
		while not self.ready and not self.is_closed():
			await asyncio.sleep(1)
		while not self.is_closed():
			if await self.should_suppress_actions():
				await asyncio.sleep(60)
				continue
			try:
				await redditForwarding(self)
			except Exception as e:
				print(f"ERROR in bgTaskSubredditForwarding: {e}")
			await asyncio.sleep(60)  # check every minute
			
	async def bgTaskBlizztrackVersionCheck(self):
		await self.wait_until_ready()
		while not self.is_closed():
			if await self.should_suppress_actions():
				await asyncio.sleep(300)
				continue
			try:
				await self.check_blizztrack_versions()
			except Exception as e:
				print(f"ERROR in bgTaskBlizztrackVersionCheck: {e}")
			await asyncio.sleep(300)

	async def check_blizztrack_versions(self,announce_if_first_run=False):
		current_versions=await blizztrack_service.get_versions()
		if not current_versions:
			logging.warning('Blizztrack check returned no data.')
			return

		previous_state=self.blizztrackVersionState if isinstance(self.blizztrackVersionState,dict) else {}
		probius_channel=self.get_channel(DiscordChannelIDs['WS.Probius'])
		if not previous_state:
			self.blizztrackVersionState=current_versions
			blizztrack_service.write_version_state(current_versions)
			if announce_if_first_run and probius_channel is not None:
				await probius_channel.send('blizztrack initial versions: '+' | '.join(self.blizztrack_summary_lines(current_versions)))
			logging.info('Blizztrack initial state stored: %s', ' | '.join(self.blizztrack_summary_lines(current_versions)))			
			return

		probius_channel=self.get_channel(DiscordChannelIDs['WS.Probius'])
		if probius_channel is None:
			self.blizztrackVersionState=current_versions
			blizztrack_service.write_version_state(current_versions)
			logging.warning('Probius channel unavailable; blizztrack updates only written to state file.')
			return

		for track_key,track_data in current_versions.items():
			previous_track=previous_state.get(track_key,{})
			previous_regions=previous_track.get('regions',{}) if isinstance(previous_track,dict) else {}
			for region,current_version in track_data.get('regions',{}).items():
				prior_version=previous_regions.get(region)
				if prior_version and prior_version!=current_version:
					logging.info('Blizztrack update detected: track=%s region=%s from=%s to=%s',track_key,region,prior_version,current_version)
					announced=self.blizztrackAnnouncedVersions.setdefault(track_key,set())
					if current_version not in announced:
						announced.add(current_version)
						ping=f'<@&{DiscordRoleIDs["Moldy"]}>'
					else:
						ping=''
					await probius_channel.send(
						f"Update detected! Game version: {track_key} updated from {prior_version} to {current_version} in region {region}.{' '+ping if ping else ''}"
					)

		self.blizztrackVersionState=current_versions
		blizztrack_service.write_version_state(current_versions)
		
async def run_blizztrack_healthcheck_mode():
	logging.info('Starting blizztrack standalone healthcheck mode (no Discord token required).')
	ok, versions = await blizztrack_service.run_healthcheck()
	logging.info('Blizztrack standalone summary: %s', ' | '.join(blizztrack_service.summary_lines(versions)))
	return 0 if ok else 1

if '--blizztrack-check' in argv:
	raise SystemExit(asyncio.run(run_blizztrack_healthcheck_mode()))

	'''async def on_user_update(self, before, after):#If a core member changes their pfp
		if before.avatar!=after.avatar:
			guild=self.get_guild(DiscordGuildIDs['WindStriders'])
			try:
				member=guild.get_member(after.id)
				if guild.get_role(DiscordRoleIDs['WS.CoreMember']) in guild.get_member(after.id).roles:pass
				else:return
			except:return
			channel=guild.get_channel(607922629902598154)
			await channel.send('<@329447886465138689>, '+member.display_name+' changed their avatar! '+(await getAvatar(self,channel,member.mention)))'''


global exitBool
exitBool=0			
while not exitBool: #Restart
	exitBool=1
	intents = discord.Intents.default()  # All but the two privileged ones
	intents.members = True  # Subscribe to the Members intent
	intents.presences = True 

	asyncio.set_event_loop(asyncio.new_event_loop())
	client = MyClient(command_prefix='!', intents=intents)
	client.run(getProbiusToken())