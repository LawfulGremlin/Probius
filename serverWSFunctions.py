import discord
import logging
import time
from discordIDs import *
from functionsPrint import printLarge

# Reaction emoji → WS role ID mapping (used by ServerRules messages)
wsReactionRoles = {
	'🇧': DiscordRoleIDs['WS.BalanceTeam'],
	'🇩': DiscordRoleIDs['WS.DraftAddict'],
	'🇸': DiscordRoleIDs['WS.Streamer'],
	'<:Tank:837022373689426061>':           DiscordRoleIDs['WS.RoleTank'],
	'<:Offlane:837022541197475941>':        DiscordRoleIDs['WS.RoleOfflane'],
	'<:RangedAssassin:837024261826019348>': DiscordRoleIDs['WS.RoleRangedAssassin'],
	'<:Healer:837024194486075443>':         DiscordRoleIDs['WS.RoleHealer'],
	'<:Flex:885591708778250350>':           DiscordRoleIDs['WS.RoleFlex'],
}

# Per-user auto-reaction list: [[user_id, emoji, last_reaction_timestamp], ...]
char = []


# ── Member lifecycle ──────────────────────────────────────────────────────────

async def ws_on_member_join(member, client):
	guild = member.guild
	await member.add_roles(guild.get_role(DiscordRoleIDs['WS.Unsorted']))
	print(member.name + ' joined')
	channel = guild.get_channel(DiscordChannelIDs['WS.General'])
	await channel.send('Welcome ' + member.mention + '! ' + client.welcomeMessage)
	try:
		for i in client.lastWelcomeImage:
			await i.delete()
	except:
		pass
	client.lastWelcomeImage = [await channel.send(file=discord.File('serverWSColors.png'))]
	client.lastWelcomeImage.append(await channel.send('https://cdn.discordapp.com/attachments/576018992624435220/743917827718905896/sorting.gif'))


async def ws_on_member_remove(member, client):
	guild = member.guild
	core_member_role = guild.get_role(DiscordRoleIDs['WS.CoreMember'])
	if core_member_role in member.roles:
		secret_cabal = guild.get_channel(DiscordChannelIDs['WS.SecretCabal'])
		await secret_cabal.send(member.name + ' left the server')
	unsorted = guild.get_role(DiscordRoleIDs['WS.Unsorted'])
	if unsorted in member.roles:
		print(member.name + ' left (unsorted)')
		channel = guild.get_channel(DiscordChannelIDs['WS.MemberLeaves'])
		await channel.send(member.name + ' (unsorted) left <:samudab:578998204142452747>')
		return
	print(member.name + ' left')
	channel = guild.get_channel(DiscordChannelIDs['WS.MemberLeaves'])
	await channel.send(member.name + ' left the server <:samudab:578998204142452747>')


async def ws_on_member_update(before, after, client):
	core = after.guild.get_role(DiscordRoleIDs['WS.CoreMember'])
	olympian = after.guild.get_role(DiscordRoleIDs['WS.Olympian'])
	if core in after.roles and core not in before.roles:
		print(f"{after.name} promoted to Core Member")
		await client.get_channel(DiscordChannelIDs['WS.SecretCabal']).send('Welcome ' + after.mention + '!')
	if olympian in after.roles and olympian not in before.roles:
		print(f"{after.name} promoted to Olympian")
		await client.get_channel(DiscordChannelIDs['WS.Pepega']).send('Welcome ' + after.mention + '!')


# ── Reaction handling ─────────────────────────────────────────────────────────

async def ws_on_reaction_add(payload, message, member, client):
	"""Handle WS-specific reaction add. Returns True if fully handled."""
	if message.id in [DiscordMessageIDs['WS.ServerRules1'], DiscordMessageIDs['WS.ServerRules2']]:
		ws_member = client.get_guild(DiscordGuildIDs['WindStriders']).get_member(payload.user_id)
		if str(payload.emoji) in wsReactionRoles:
			role = client.get_guild(DiscordGuildIDs['WindStriders']).get_role(wsReactionRoles[str(payload.emoji)])
			await ws_member.add_roles(role)
			print(f"{ws_member.name} assigned role {role.name} via reaction")
		if str(payload.emoji) == '🇱':
			await giveLfgRoles(ws_member, client)
		return True
	if str(payload.emoji) == '⚽' and message.channel.id == DiscordChannelIDs['WS.General']:
		await sortFromReaction(message, member.id, client)
		return True
	return False


async def ws_on_reaction_remove(payload, message, member, client):
	"""Handle WS-specific reaction remove. Returns True if fully handled."""
	if message.id in [DiscordMessageIDs['WS.ServerRules1'], DiscordMessageIDs['WS.ServerRules2']]:
		ws_member = client.get_guild(DiscordGuildIDs['WindStriders']).get_member(payload.user_id)
		if str(payload.emoji) in wsReactionRoles:
			await ws_member.remove_roles(client.get_guild(DiscordGuildIDs['WindStriders']).get_role(wsReactionRoles[str(payload.emoji)]))
		if str(payload.emoji) == '🇱':
			await removeLfgRoles(ws_member, client)
		return True
	return False


async def ws_check_reddit_downvote(message, member, client):
	"""Handle 👎 on WS.RedditPosts (bonk instead of delete). Returns True if handled."""
	if message.channel.id == DiscordChannelIDs['WS.RedditPosts']:
		output = member.mention + '<:bonk:761981366744121354>'
		await client.get_channel(DiscordChannelIDs['WS.General']).send(output)
		return True
	return False


# ── Message handling ──────────────────────────────────────────────────────────

async def ws_on_message(message, client):
	"""Handle WS-specific logic in on_message (called before bot commands)."""
	for i in char:
		if message.author.id == i[0] and time.time() - i[2] > 300 and message.channel.guild.id == DiscordGuildIDs['WindStriders']:
			i[2] = time.time()
			await message.add_reaction(i[1])
	if ('@everyone' in message.content or '@here' in message.content) and message.guild.id == DiscordGuildIDs['WindStriders']:
		await message.add_reaction('<:LEVEL2AAAA:923294790278324315>')
	if message.embeds and message.channel.id == DiscordChannelIDs['WS.General'] and 'View tweet' in message.content:
		await message.channel.send(message.embeds[0].thumbnail.url)
		await message.edit(suppress=True)
	if message.author.id == DiscordUserIDs['BlizztrackBot'] and message.channel.id == DiscordChannelIDs['WS.General']:
		try:
			e = message.embeds[0].fields[3]
			if e.name == 'Full patch notes at':
				output = 'Patch notes!\n' + e.value
				await message.channel.send('@everyone ' + output)
		except:
			pass
	if not message.author.bot:
		try:
			if DiscordRoleIDs['WS.Unsorted'] in [role.id for role in message.author.roles]:
				await sortFromReaction(message, DiscordUserIDs['Probius_asddsa-token'], client)
		except:
			pass
	await iAmName(message)


async def ws_on_message_edit(before, after, client):
	"""Handle WS-specific logic in on_message_edit."""
	if after.embeds and after.channel.id == DiscordChannelIDs['WS.General'] and 'New dev tweet!' in after.content:
		await after.channel.send(after.embeds[0].thumbnail.url)
		await after.edit(suppress=True)
	if not before.author.bot:
		try:
			if DiscordRoleIDs['WS.Unsorted'] in [role.id for role in after.author.roles]:
				await sortFromReaction(after, DiscordUserIDs['Probius_asddsa-token'], client)
		except:
			pass


# ── Ready ─────────────────────────────────────────────────────────────────────

async def ws_on_ready(client):
	"""Initialise WS-specific client state on bot ready."""
	client.rulesChannel = client.get_channel(DiscordChannelIDs['WS.ServerRules'])
	if client.rulesChannel is not None:
		client.welcomeMessage = (
			'Please read ' + client.rulesChannel.mention +
			' and type here your **`Region`, `Rank`, and `Preferred Colour`**, separated by commas,'
			' to get sorted and unlock the rest of the channels <:OrphAYAYA:657172520092565514>'
		)
	else:
		client.welcomeMessage = (
			'Please read the rules channel and type here your **`Region`, `Rank`, and `Preferred Colour`**,'
			' separated by commas, to get sorted and unlock the rest of the channels <:OrphAYAYA:657172520092565514>'
		)
		logging.warning("rulesChannel not found; welcomeMessage uses fallback text.")


# ── Commands ──────────────────────────────────────────────────────────────────

async def ws_command_unsorted(message, client):
	if DiscordRoleIDs['WS.Olympian'] in [role.id for role in message.author.roles]:
		channel = client.get_channel(DiscordChannelIDs['WS.General'])
		role = channel.guild.get_role(DiscordRoleIDs['WS.Unsorted'])
		await channel.send('Note to all ' + role.mention + ': ' + client.welcomeMessage)
		await channel.send(
			content='https://cdn.discordapp.com/attachments/576018992624435220/743917827718905896/sorting.gif',
			file=discord.File('serverWSColors.png'),
		)


async def ws_command_byprobiusbepurged(message, client):
	if DiscordRoleIDs['WS.Olympian'] in [role.id for role in message.author.roles]:
		people = [i for i in message.channel.guild.members if DiscordRoleIDs['WS.Unsorted'] in [role.id for role in i.roles]]
		print(f"{message.author.name} purging {len(people)} unsorted members")
		for person in people:
			await message.channel.guild.kick(person, reason='Did not sort in time!')
		print(f"Purge complete: {len(people)} members kicked")


# ── Utility (WS-only, previously in miscFunctions.py) ────────────────────────

async def deleteMessages(author, ping, client):
	guild = client.get_guild(DiscordGuildIDs['WindStriders'])
	if DiscordRoleIDs['WS.Olympian'] not in [role.id for role in author.roles]:
		return
	print(f"{author.name} deleting messages from {ping}")
	userId = int(ping.replace(' ', '').replace('!', '')[2:-1])
	deletedCount = 0
	for channel in guild.text_channels:
		try:
			async for message in channel.history(limit=20):
				if message.author.id == userId:
					await message.delete()
					deletedCount += 1
		except:
			pass
	print(f"Deleted {deletedCount} messages from {ping}")
	await guild.get_channel(DiscordChannelIDs['WS.Pepega']).send('Deleted ' + str(deletedCount) + ' messages from ' + ping)


async def coaching(message):
	if DiscordRoleIDs['WS.Coach'] in [i.id for i in message.author.roles]:
		await message.channel.send(
			'<@&' + str(DiscordRoleIDs['WS.Streamer']) + '> Coach ' + message.author.mention +
			' is running a live session! Head down to <#' + str(DiscordChannelIDs['WS.CoachingSession']) + '> to check it out!'
		)
	else:
		await message.channel.send(message.author.mention + ' you must be a coach to host coaching sessions.')


async def wrongChannelBuild(message):
	await message.guild.get_channel(DiscordChannelIDs['WS.Probius']).send(
		message.author.mention + ' Please call builds in this channel to avoid cluttering the other channels!'
	)
	await message.guild.get_channel(DiscordChannelIDs['WS.Probius']).send(
		'https://cdn.discordapp.com/attachments/604394753722941451/892843516722569266/help_probius_clean_up1.png'
	)


async def iAmName(message):
	if message.channel.guild.id != DiscordGuildIDs['WindStriders'] or message.author.id != DiscordUserIDs['TestServer']:
		return
	index = message.content.lower().find("i'm ") + 4
	if index == 3:
		index = message.content.lower().find("i am ") + 5
		if index == 4:
			return
	wordList = message.content[index:].split(' ')
	newName = wordList.pop(0)
	for word in wordList:
		proposedName = f"{newName} {word}"
		if len(proposedName) < 32:
			newName = proposedName
		else:
			break
	if len(newName) <= 2:
		return
	await message.author.edit(nick=newName)


# ── LFG (Looking for Group) ───────────────────────────────────────────────────

def roleAliases(role):
	role='grandmaster' if role=='gm' else role
	role='master' if role=='masters' else role
	role='diamond' if role=='dia' else role
	role='platinum' if role=='plat' else role
	role='unranked' if role in ['ur','none','qm'] else role

	role='eu' if role=='europe' else role
	role='na' if role in ['northamerica','us','america','americas','usa'] else role
	role='latam' if role in ['br','brazil'] else role

	return role

async def lfg(channel,text,client):
	inputRoles=[roleAliases(j) for j in text.replace(' ','').split(',')]
	roles=[i for i in channel.guild.roles if i.name.lower().replace(' ','') in inputRoles]
	people=[i for i in channel.guild.members if len(roles)==sum(1 for j in roles if j in i.roles)]
	lfgRole=client.get_guild(DiscordGuildIDs['WindStriders']).get_role(DiscordRoleIDs['WS.LFG'])
	if len(roles)!=len(inputRoles):
		await channel.send('Invalid roles!')
	elif people:
		peopleNames=[]
		for i in people:
			name=i.nick if i.nick else i.name
			peopleNames.append('**'+name+'**' if lfgRole in i.roles else name)
		await printLarge(channel,', '.join(peopleNames),',')
	else:
		await channel.send('No people found!')


# ── Role sorting ──────────────────────────────────────────────────────────────

async def trim(text):
	toRemove=[' ','#','<@&{}>'.format(DiscordRoleIDs['WS.Olympian']),'*','\n','league','and']
	text=text.lower()
	for i in toRemove:
		text=text.replace(i,'')
	if '<@' in text:
		text=text[:text.index('<')]+text[1+text.index('>'):]#Remove pings
	return text

async def sort(roles,member,olympian,client):
	guild=client.get_guild(DiscordGuildIDs['WindStriders'])#Wind Striders
	channel=guild.get_channel(DiscordChannelIDs['WS.General'])#general
	if DiscordRoleIDs['WS.Olympian'] not in [role.id for role in olympian.roles]:
		return
	if len(roles)!=3:
		return
	#Colours
	blue1=guild.get_role(DiscordRoleIDs['WS.ColourBlue'])
	magenta=guild.get_role(DiscordRoleIDs['WS.ColourMagenta'])
	#Ranks and regions
	gm=guild.get_role(DiscordRoleIDs['WS.GrandMaster'])
	sea=guild.get_role(DiscordRoleIDs['WS.RegionSEA'])

	unsorted=guild.get_role(DiscordRoleIDs['WS.Unsorted'])

	if unsorted not in member.roles:
		return
	roles=list(set(roles))
	if len(roles)!=3:
		return
	rolesToAdd=[]
	for role in roles:
		try:
			role=roleAliases(role)
			for i in sorted(guild.roles):
				if (i<=blue1 and i>=magenta) or (i<=gm and i>=sea):
					if await trim(i.name)==await trim(role):
						rolesToAdd.append(i)
					elif await trim(i.name)==await trim(''.join([i for i in role if not i.isdigit()])):#Rank numbers
						rolesToAdd.append(i)
					elif await trim(i.name)==await trim(role+'1'):#Add colour #1
						rolesToAdd.append(i)
					else:
						continue
					raise Exception('Role done!')
		except:
			pass
	if len(rolesToAdd)!=3:
		return
	memberRole=guild.get_role(DiscordRoleIDs['WS.Member'])
	rolesToAdd.append(memberRole)
	await member.add_roles(*rolesToAdd)
	await member.remove_roles(unsorted)
	print(f"{member.name} sorted with roles: {', '.join(r.name for r in rolesToAdd)}")
	await channel.send('**'+member.name+'** has been sorted!')
	await giveLfgRoles(member,client)

async def sortFromMessage(text,message,client):
	unsortedMember,text=text.split('>')
	unsortedMember+='>'
	text=await trim(text)
	guild=client.get_guild(DiscordGuildIDs['WindStriders'])#Wind Striders
	unsortedMember=guild.get_member(int(unsortedMember.replace(' ','')[2:-1].replace('!','')))

	roles=text.split(',')
	if roles[0]=='':
		roles.pop(0)
	await sort(roles,unsortedMember,message.author,client)

async def sortFromReaction(message,reacterID,client):
	roles=await trim(message.content)
	if '/' in roles:
		roles=roles.split('/')
	else:
		roles=roles.split(',')
	unsortedMember=message.author
	guild=client.get_guild(DiscordGuildIDs['WindStriders'])
	olympian=guild.get_member(int(reacterID))
	await sort(roles,unsortedMember,olympian,client)

async def giveLfgRoles(member,client):
	reaction=[i for i in (await (await client.fetch_channel(DiscordChannelIDs['WS.ServerRules'])).fetch_message(DiscordMessageIDs['WS.ServerRules1'])).reactions if i.emoji=='🇱'][0]
	users=await reaction.users().flatten()
	if member.id not in (i.id for i in users):
		return
	for i in [i.id for i in member.roles]:
		if i in client.wsLfgRoles:
			await member.add_roles(client.get_guild(DiscordGuildIDs['WindStriders']).get_role(client.wsLfgRoles[i]))

async def removeLfgRoles(member,client):
	invertedDict={v: k for k, v in client.wsLfgRoles.items()}
	for i in [i.id for i in member.roles]:
		if i in invertedDict:
			await member.remove_roles(client.get_guild(DiscordGuildIDs['WindStriders']).get_role(i))
