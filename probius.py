#A HotS Discord bot
#Call in Discord with [hero/modifier]
#Modifier is hotkey or talent tier
#Data is pulled from HotS wiki
#Project started on 14/9-2019

import asyncio
import discord
from sys import argv
import logging

from functionsBasic import *		#Edge cases and help message
from heroesTalents import *		#The function that imports the hero pages
from serverWSFunctions import *		#Wind Striders server-specific features
from communityReddit import *
from discordIDs import *
from functionsBlizztrack import BlizztrackService, run_blizztrack_healthcheck_mode
from messageCommands import mainProbius
from messageReactions import handle_author_reactions, handle_baelog, is_advisor_message
from discordToken import getDiscordToken

logging.basicConfig(level=logging.INFO)

botChannels={'Wind Striders':DiscordChannelIDs['WS.Probius']}

SUPPRESS_USER_IDS = [#It can generally be assumed that suppression is not active.
	DiscordUserIDs['Probius_asddsa-token'],  # Probius (Asddsa's token/instance)
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
		self.restart=False
		self.ready=False#Wait until ready before taking commands
		self.activeSuppressIDs=[]#Populated in on_ready, excludes own user ID

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
			for user_id in self.activeSuppressIDs:
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
		self.activeSuppressIDs=[uid for uid in SUPPRESS_USER_IDS if uid != self.user.id]
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
				if command == 'mepeat' and len(txt) == 2 and message.author.id in ProbiusPrivilegeIDs:
					# Repeat the message, then optionally delete the original (like [repeat])
					await message.channel.send(message.content.split('[')[1].split('/')[1].split(']')[0])
					await message.delete()
					return
		if await self.should_suppress_actions():
			return
		await super().on_message(message) if hasattr(super(), "on_message") else None
		await ws_on_message(message, self)
		pingList=[PingForwardIDs[i] for i in PingForwardIDs if '@'+i in message.content.replace(' ','').lower()]
		if pingList:
			await message.channel.send(' '.join(['<@'+str(i)+'>' for i in pingList]))
		await handle_author_reactions(message)
		if message.author.bot:#Don't respond to bots
			return
		await handle_baelog(message, self)
		if self.ready==False:
			return
		elif '[' in message.content:
			texts=findTexts(message)
			await mainProbius(self,message,texts,blizztrack_service)
		await removeEmbeds(message)

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
				await mainProbius(self,after,newTexts,blizztrack_service)

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
		if is_advisor_message(message):
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

		if member.id in ProbiusAuthorIDs:#Reaction copying
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
						ping=f'<@&{DiscordRoleIDs["WS.Moldy"]}>'
					else:
						ping=''
					await probius_channel.send(
						f"Update detected! Game version: {track_key} updated from {prior_version} to {current_version} in region {region}.{' '+ping if ping else ''}"
					)

		self.blizztrackVersionState=current_versions
		blizztrack_service.write_version_state(current_versions)

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


while True: #Restart
	intents = discord.Intents.default()  # All but the two privileged ones
	intents.members = True  # Subscribe to the Members intent
	intents.presences = True

	asyncio.set_event_loop(asyncio.new_event_loop())
	client = MyClient(command_prefix='!', intents=intents)
	client.run(getDiscordToken())
	if not client.restart:
		break
