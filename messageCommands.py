import random
import discord

from heroesAliases import *
from functionsPrint import *
from heroesTalents import *
from heroesEmojis import *
from functionsBasic import *
from heroesTalentsCompare import *
from serverWSFunctions import *
from communityBuilds import *
from communityRotation import *
from heroesQuotes import *
from heroesDraft import *
from communityReddit import *
from communityPatchNotes import *
from heroesMaps import *
from discordIDs import *

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
ptrAliases=['ptr']

drafts={}#Outside of client so it doesn't reset on periodic restarts or [restart]
lastDraftMessageDict={}
draftNames={}

async def mainProbius(client,message,texts,blizztrack_service):
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
		if command=='exit' and message.author.id in ProbiusPrivilegeIDs:
			await client.close()
		if command in restartAliases and message.author.id in ProbiusPrivilegeIDs:
			client.restart=True
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
			await message.channel.send(file=discord.File('serverWSColors.png'))
			continue
		if message.author.id in ProbiusPrivilegeIDs:
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
			if message.author.id in ProbiusAuthorIDs:
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
		if command in ptrAliases and len(text) == 2:
			hero = aliases(text[1])
			live_v = readVersion('.hversion')
			test_v = readVersion('.hversion-test')
			if not (test_v and live_v and parseVersion(test_v) > parseVersion(live_v)):
				await message.channel.send('No PTR data available.')
				continue
			if hero not in client.heroPages or hero not in client.heroPages_test:
				await message.channel.send(f'No data found for {text[1]}.')
				continue
			(abilities, talents) = client.heroPages[hero]
			(test_abilities, test_talents) = client.heroPages_test[hero]
			sections = diffHeroPtrChanges(abilities, talents, test_abilities, test_talents, live_v, test_v)
			if not sections:
				await message.channel.send(f'No PTR changes for {hero.replace("_", " ")}.')
				continue
			header = f'**PTR Changes: {hero.replace("_", " ")} [{live_v} → {test_v}]**\n\n'
			await printLarge(message.channel, header + '\n\n'.join(sections))
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
