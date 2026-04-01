import discord
import time
from discordIDs import *
from sorting import sortFromReaction, giveLfgRoles, removeLfgRoles

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
	client.lastWelcomeImage = [await channel.send(file=discord.File('WS colours.png'))]
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
		await client.get_channel(DiscordChannelIDs['WS.SecretCabal']).send('Welcome ' + after.mention + '!')
	if olympian in after.roles and olympian not in before.roles:
		await client.get_channel(DiscordChannelIDs['WS.Pepega']).send('Welcome ' + after.mention + '!')


# ── Reaction handling ─────────────────────────────────────────────────────────

async def ws_on_reaction_add(payload, message, member, client):
	"""Handle WS-specific reaction add. Returns True if fully handled."""
	if message.id in [DiscordMessageIDs['WS.ServerRules1'], DiscordMessageIDs['WS.ServerRules2']]:
		ws_member = client.get_guild(DiscordGuildIDs['WindStriders']).get_member(payload.user_id)
		if str(payload.emoji) in wsReactionRoles:
			await ws_member.add_roles(client.get_guild(DiscordGuildIDs['WindStriders']).get_role(wsReactionRoles[str(payload.emoji)]))
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
				await sortFromReaction(message, DiscordUserIDs['Probius'], client)
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
				await sortFromReaction(after, DiscordUserIDs['Probius'], client)
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
		print("WARNING: rulesChannel not found; welcomeMessage uses fallback text.")


# ── Commands ──────────────────────────────────────────────────────────────────

async def ws_command_unsorted(message, client):
	if DiscordRoleIDs['WS.Olympian'] in [role.id for role in message.author.roles]:
		channel = client.get_channel(DiscordChannelIDs['WS.General'])
		role = channel.guild.get_role(DiscordRoleIDs['WS.Unsorted'])
		await channel.send('Note to all ' + role.mention + ': ' + client.welcomeMessage)
		await channel.send(
			content='https://cdn.discordapp.com/attachments/576018992624435220/743917827718905896/sorting.gif',
			file=discord.File('WS colours.png'),
		)


async def ws_command_byprobiusbepurged(message, client):
	if DiscordRoleIDs['WS.Olympian'] in [role.id for role in message.author.roles]:
		people = [i for i in message.channel.guild.members if DiscordRoleIDs['WS.Unsorted'] in [role.id for role in i.roles]]
		for person in people:
			await message.channel.guild.kick(person, reason='Did not sort in time!')


# ── Utility (WS-only, previously in miscFunctions.py) ────────────────────────

async def deleteMessages(author, ping, client):
	guild = client.get_guild(DiscordGuildIDs['WindStriders'])
	if DiscordRoleIDs['WS.Olympian'] not in [role.id for role in author.roles]:
		return
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
