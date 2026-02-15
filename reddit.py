import asyncio
import aiohttp
import logging
import re
from rotation import *
from printFunctions import printLarge
from discordIDs import *

LOGGER = logging.getLogger(__name__)

redditors=['Asddsa76', 'Blackstar_9', 'Spazzo965', 'SomeoneNew666', 'joshguillen', 'SotheBee', 'AnemoneMeer', 'Pscythic', 'Elitesparkle', 'slapperoni', 
'secret3332', 'Carrygan_', 'Archlichofthestorm', 'Gnueless', 'ThatDoomedStudent', 'InfiniteEarth', 'SamiSha_', 'twinklesunnysun', 'Pelaberus', 'KillMeWithMemes',
'MarvellousBee','Naturage','Derenash','Riokaii','Demon_Ryu','hellobgs','Beg_For_Mercy','Russisch','Valamar1732','ArashiNoShad0w','lemindhawk','Goshin26',
'TiredZealot','MasterAblar','SHreddedWInd','MrWilbus','NotBelial','Dark_Polaroid','HeroesProfile','nexusschoolhouse','Nightterror0','WorstMedivhKR','Babaguscooties',
'JozefxDark']

discordnames={'Pscythic':'Soren Lily', 'SotheBee':'Sothe', 'slapperoni':'slap','secret3332':'SecretChaos','Archlichofthestorm':'Trolldaeron','ThatDoomedStudent':'Carbon','InfiniteEarth':'Flash',
'KillMeWithMemes':'Nick','Demon_Ryu':'Messa','Russisch':'Ekata','ArashiNoShad0w':'LeviathaN','lemindhawk':'MindHawk','Nightterror0':'Deafwing', 'Dark_Polaroid':'Medicake','Babaguscooties':'Labreris'}

#Posts with these in title gets forwarded regardless of author
keywords={
'Genji':[DiscordUserIDs['Weebatsu']],
'Samuro':[DiscordUserIDs['Blackstorm']],
'Zera':[DiscordUserIDs['Derenash']],
'Valeera':[684944498039455781, 738440231568801914],
'Orphea':[410481791204327424, 738440231568801914],
'Deathwing':[204893952908853248],
'Time stop':[268871972778147870],
'Li-Ming':[738440231568801914]}

# --- Restart-only dedupe: scan last N messages in target channels once on startup ---
REDDIT_ID_RE = re.compile(
	r'https?://(?:www\.|old\.)?reddit\.com/r/heroesofthestorm/comments/([a-z0-9]+)',
	re.IGNORECASE
)

DISCORD_REDDIT_DEDUPE_CHANNEL_IDS = {
	DiscordChannelIDs['LoggingChannel'],
	DiscordChannelIDs['RedditPosts'],
	DiscordChannelIDs['General'],
	DiscordChannelIDs['NormieHeroes'],
	DiscordChannelIDs['Samuro'],
	222817241249480704,  # special channel used for nexusschoolhouse/Spazzo965 cases
}

DISCORD_REDDIT_DEDUPE_LIMIT = 50

def _extract_reddit_ids_from_text(text):
	if not text:
		return set()
	return {m.group(1).lower() for m in REDDIT_ID_RE.finditer(text)}

async def _get_channel(client, channel_id):
	# cache might be cold right after startup; fetch is more reliable
	channel = client.get_channel(channel_id)
	if channel is None:
		try:
			channel = await client.fetch_channel(channel_id)
		except Exception:
			return None
	return channel

async def prime_recent_discord_reddit_ids(client):
	"""
	Run ONCE per process start:
	- scan last DISCORD_REDDIT_DEDUPE_LIMIT messages in each target channel
	- collect reddit post IDs already present
	"""
	if getattr(client, "_recent_discord_reddit_ids_primed", False):
		return
	client._recent_discord_reddit_ids_primed = True
	client.recentDiscordRedditIDs = set()

	for channel_id in DISCORD_REDDIT_DEDUPE_CHANNEL_IDS:
		channel = await _get_channel(client, channel_id)
		if channel is None:
			LOGGER.warning("prime_recent_discord_reddit_ids: channel %s unavailable", channel_id)
			continue

		try:
			async for msg in channel.history(limit=DISCORD_REDDIT_DEDUPE_LIMIT):
				client.recentDiscordRedditIDs |= _extract_reddit_ids_from_text(getattr(msg, "content", ""))
		except Exception as e:
			# Most common causes: missing "Read Message History" permission
			LOGGER.warning("prime_recent_discord_reddit_ids: can't read channel %s (%s)", channel_id, e)

	LOGGER.info(
		"prime_recent_discord_reddit_ids: loaded %d reddit ids from recent history",
		len(client.recentDiscordRedditIDs)
	)

async def getPostInfo(post):
	title=post.split('", "')[0]
	title=title.replace('\u2019',"'")
	post=post.split('"author": "')[1]
	author=post.split('"')[0]
	post=post.split('"permalink": "')[1]
	urlID='/'.join(post.split('/')[:5])
	url='https://www.reddit.com'+urlID
	title=title.encode().decode('unicode_escape')
	return [title,author,url]

async def fetch(session, url):
	async with session.get(url) as response:
		return await response.text()

async def titleTrim(title):#Don't remove spaces because of Cho
	a={'_':'\_','&amp;':'&'}
	for i in a.keys():
		title=title.replace(i,a[i])
	return title

async def fillPreviousPostTitles(client):#Called on startup
	await client.wait_until_ready()
	async with aiohttp.ClientSession() as session:
		page = await fetch(session, 'https://old.reddit.com/r/heroesofthestorm/new.api?limit=100&sort=new')
		posts=page.replace('"is_gallery": true, ','').split('"clicked": false, "title": "')[1:]
		output=[]
		for post in posts:
			try:
				[title,author,url] = await getPostInfo(post)#Newest post that has been checked
				output.append(title)
				title=await titleTrim(title)
				client.seenPosts.append([title,author,url])
				if author in redditors or sum(1 for i in keywords if i.lower() in title.lower()) or 'Blizz_' in author:
					client.forwardedPosts.append([title,author,url])
			except:pass
		client.forwardedPosts=client.forwardedPosts[::-1]
		return output

async def redditForwarding(client):#Called every 60 seconds
	async def send_to_channel(channel_id, message):
		channel = client.get_channel(channel_id)
		if channel is None:
			LOGGER.warning('redditForwarding skipped send: channel %s unavailable', channel_id)
			return False
		await channel.send(message)
		return True

	async with aiohttp.ClientSession() as session:
		page = await fetch(session, 'https://old.reddit.com/r/heroesofthestorm/new.api')
		posts=page.replace('"is_gallery": true, ','').split('"clicked": false, "title": "')[1:]
		for post in posts:
			try:
				[title,author,url] = await getPostInfo(post)
			except:continue
			# Restart-only dedupe
			reddit_id_match = REDDIT_ID_RE.search(url)
			if reddit_id_match and hasattr(client, "recentDiscordRedditIDs"):
				reddit_id = reddit_id_match.group(1).lower()
				if reddit_id in client.recentDiscordRedditIDs:
					if title not in client.seenTitles:
						client.seenTitles.append(title)
					continue
			if title not in client.seenTitles:#This post hasn't been processed before
				client.seenTitles.append(title)
				title=await titleTrim(title)
				url='\n'+url
				client.seenPosts.append([title,author,url])
				if author in redditors or sum(1 for i in keywords if i.lower() in title.lower()) or 'Blizz_' in author:
					client.forwardedPosts.append([title,author,url])
					if author=='nexusschoolhouse':
						await send_to_channel(222817241249480704, '**{}**: '.format(title)+url)
					if author=='Spazzo965' and ('CCL' in title or 'Undocumented' in title):
						await send_to_channel(222817241249480704, '**{}**: '.format(title)+url)

					toPing=[]
					for i in keywords:
						if i.lower() in title.lower():
							toPing+=keywords[i]
					if toPing:
						toPing=' '.join(['<@'+str(i)+'>' for i in toPing])

					if author in redditors:
						if author in discordnames:
							author=discordnames[author]
						await send_to_channel(DiscordChannelIDs['LoggingChannel'], '`{} by {}`'.format(title,author))#log
						await send_to_channel(DiscordChannelIDs['RedditPosts'], '**{}** by {}: {}'.format(title,author,url))#reddit-posts
						if toPing:
							await send_to_channel(DiscordChannelIDs['General'], '**{}** by {}: {}\n{}'.format(title,author,url,toPing))#general
						else:
							await send_to_channel(DiscordChannelIDs['General'], '**{}** by {}: {}'.format(title,author,url))#general
						if author=='Gnueless' and 'rotation' in title.lower():
							general_channel = client.get_channel(DiscordChannelIDs['General'])
							if general_channel is not None:
								await rotation(general_channel)
							else:
								LOGGER.warning('redditForwarding skipped rotation post: General channel unavailable')
					else:
						await send_to_channel(DiscordChannelIDs['LoggingChannel'], '`{} by {}`'.format(title,author))#log
						channel=[DiscordChannelIDs['NormieHeroes'],DiscordChannelIDs['Samuro']]['samuro' in title.lower()]#Normie-heroes or Samuro
						await send_to_channel(channel, '**{}** {}{}'.format(title,toPing,url))

async def redditSearch(client,message,text):
	output=''
	for i in client.seenPosts:
		author=i[1]
		if author in discordnames:
			author=discordnames[author]
		if text.lower() in i[0].lower():
			output+='**{}** by {}: <{}>\n'.format(i[0], author, i[2])
	await printLarge(message.channel,output)

async def reddit(client,message,text):
	if len(text)==2:
		if not text[1].isnumeric():
			await redditSearch(client,message,text[1])
			return
		cutoff=-int(text[1])
	else:
		cutoff=0
	output='Recent Reddit posts:\n'
	for i in client.forwardedPosts[cutoff:]:
		author=i[1]
		if author in discordnames:
				author=discordnames[author]
		output+='**{}** by {}: <{}> \n'.format(i[0], author, i[2])
	await printLarge(message.channel,output)