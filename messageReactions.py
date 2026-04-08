from discordIDs import *

async def handle_author_reactions(message):
	"""Auto-reactions and responses triggered by message author."""
	if message.author.id == DiscordUserIDs['Gooey']:
		if 'explod' in message.content.lower():
			await message.add_reaction('<:explodes:955458830244913153>')
		if 'a' == message.content.lower():
			await message.add_reaction("🅰")
	if message.author.id == 0:  # Birthday cake
		await message.add_reaction('🍰')

async def handle_baelog(message, client):
	if 'baelog' in message.content.lower():
		if message.channel.guild.id == DiscordGuildIDs['WindStriders']:
			await client.get_channel(DiscordChannelIDs['WS.Probius']).send(message.author.mention+'Ba**LE**og\nhttps://i.imgur.com/Nrcg11Z.png')
		else:
			await message.channel.send('Ba**LE**og\nhttps://i.imgur.com/Nrcg11Z.png')

def is_advisor_message(message):
	return message.author.id == DiscordUserIDs['AdvisorBot']
