from heroesAliases import *
import asyncio
import re
from discordIDs import *

allHeroes={
	'bruiser':['Artanis', 'Chen', 'D.Va', 'Deathwing', 'Dehaka', 'Gazlowe', 'Hogger','Imperius', 'Leoric', 'Malthael', 'Ragnaros', 'Rexxar', 'Sonya', 'Thrall', 'Varian', 'Xul', 'Yrel'],
	'healer':['Alexstrasza', 'Ana', 'Anduin', 'Auriel', 'Brightwing', 'Deckard', 'Kharazim', 'Li_Li', 'Lt._Morales', 'Lúcio', 'Malfurion', 'Rehgar', 'Stukov', 'Tyrande', 'Uther', 'Whitemane'],
	'mage':['Azmodan', 'Chromie', 'Gall', "Gul'dan", 'Jaina', "Kael'thas", "Kel'Thuzad", 'Li-Ming', 'Mephisto', 'Nazeebo', 'Orphea', 'Probius', 'Tassadar'],
	'marksman':['Cassia', 'Falstad', 'Fenix', 'Genji', 'Greymane', 'Hanzo', 'Junkrat', 'Lunara', 'Nova', 'Raynor', 'Sgt._Hammer', 'Sylvanas', 'Tracer', 'Tychus', 'Valla', 'Zagara',"Zul'jin"],
	'melee':['Alarak', 'Illidan', 'Kerrigan', 'Maiev', 'Murky', 'Qhira', 'Samuro', 'The_Butcher', 'Valeera', 'Zeratul'],
	'support':['Abathur', 'Medivh', 'The_Lost_Vikings', 'Zarya'],
	'tank':["Anub'arak", 'Arthas', 'Blaze', 'Cho', 'Diablo', 'E.T.C.', 'Garrosh', 'Johanna', "Mal'Ganis", 'Mei', 'Muradin', 'Stitches', 'Tyrael']
}

def getHeroes():#Returns an alphabetically sorted list of all allHeroes.
	return sorted([j for i in allHeroes.values() for j in i])

async def getRoleHeroes(role):
	if role=='ranged':
		return allHeroes['mage']+allHeroes['marksman']
	elif role=='assassin':
		return (await getRoleHeroes('ranged'))+allHeroes['melee']
	else:
		return allHeroes[role]

async def heroes(message,text,channel,client):
	#['hero', 'heroes', 'bruiser', 'healer', 'support', 'ranged', 'melee', 'assassin', 'mage', 'marksman', 'tank']
	role=text[0].replace('marksmen','marksman').replace('offlaner','bruiser')
	if role[-1]=='s':role=role[:-1]
	if len(text)==1:
		if role in ['hero', 'heroe']:
			await channel.send('\n'.join(['**'+i.capitalize()+':** '+', '.join(allHeroes[i]).replace('_',' ') for i in allHeroes]))
		elif role=='assassin':
			await channel.send('\n'.join(['**'+i.capitalize()+':** '+', '.join(allHeroes[i]).replace('_',' ') for i in ['mage', 'marksman', 'melee']]))
		elif role=='ranged':
			await channel.send('\n'.join(['**'+i.capitalize()+':** '+', '.join(allHeroes[i]).replace('_',' ') for i in ['mage', 'marksman']]))
		else:
			await channel.send('**'+role.capitalize()+':** '+', '.join(allHeroes[role]).replace('_',' '))
	else:
		if role in ['hero', 'heroe']:
			await printAll(client,message,text[1])
		else:
			await printAll(client,message,text[1], 1, await getRoleHeroes(role))
def printTier(talents,tier):#Print a talent tier
	output=''
	for i in talents[tier]:
		output+=i+'\n'
	return output

def printAbility(abilities,hotkey):#Prints abilities with matching hotkey
	output=''
	for ability in abilities:
		if '**['+hotkey.upper()+']' in ability:
			output+=ability+'\n'
	return output

def deepAndShallowSearchFoundBool(ability,string,deep):#Python3.5 doesn't allow async functions inside list comprehension :(
	if not deep:
		ability=ability.split(':**')[0]
	if string in ability.lower():
		return 1

	if string==''.join([i[0] for i in ability.lower().split(':**')[0].split(' ')[1:]]):
		return 1
	return 0

async def printCompactBuild(client,channel,text):
	#bot channel: posts whole thing
	#outside bot channel: post formatted query and name of talents, and reacts :thumb up:
	#when reacted to, print whole thing
	from heroesTalents import get_hero_data
	build,hero=text.split(',')#Example: T0230303,DVa
	hero=aliases(hero)
	(abilities,talents)=await get_hero_data(hero)
	build=build.replace('q','1').replace('w','2').replace('e','3').replace('r','4').replace('t','5')

	#Check for malicious input, since the build will be repeated back
	for i in build[1:]:
		if i not in '0123456789':return

	if channel.id in client.botChannels.values():
		await printBuild(channel,build,talents)
		return

	output='Talent build [T'+build[1:]+','+hero+']: '
	talentsToPrint=[]
	for j,i in enumerate(build[1:]):
		if i=='0':continue
		talentsToPrint.append(talents[j][int(i)-1].split('**')[1].split('] ')[1].replace(':',''))
	output+=', '.join(talentsToPrint)
	message=await channel.send(output)
	await message.add_reaction('👍')

async def printBuild(channel,build,talents):#Posts all tooltips on reactions, or when posted in bot channel
	output=[]
	for j,i in enumerate(build[1:]):
		if i=='0':continue
		output.append(talents[j][int(i)-1])
	await printLarge(channel,'\n'.join(output))

async def printBuildFromReaction(client,message):
	from heroesTalents import get_hero_data
	build,hero=message.content.split('[')[1].split(']')[0].split(',')
	(abilities,talents)=await get_hero_data(hero)
	await printBuild(message.channel,build,talents)

async def addUnderscoresAndNewline(namelist,ability):
	indices=[]
	for i in namelist:
		#ability=ability.replace(i,'__'+i+'__').replace(i.capitalize(),'__'+i.capitalize()+'__').replace(i.title(),'__'+i.title()+'__')
		indicesA=[m.start() for m in re.finditer(i,ability.lower())]
		indices+=[j+len(i) for j in indicesA]+indicesA
	indices.sort(key=lambda x:-x)#Sort in descending order
	for i in indices:
		ability=ability[:i]+'__'+ability[i:]
	return ability+'\n'

async def printAbilityTalents(message,abilities,talents,hotkey,hero):
	#Get ability name from hotkey
	abilityName=printAbility(abilities,hotkey).split('] ')[1].split(':')[0]
	output='\n'.join(ability for ability in abilities if abilityName in ability)

	#Search in talents for that ability
	output2=''
	levelTiers=[0,1,2,3,4,5,6]
	if hero=='Varian':
		del levelTiers[1]
	elif hero in ['Tracer','Deathwing']:
		pass
	else:
		del levelTiers[3]
	for i in levelTiers:
		talentTier=talents[i]
		for talent in talentTier:
			if abilityName in talent:
				output2+='\n'+talent

	if output2:
		output+=output2
	await printLarge(message.channel,output)

_QUERY_KEYWORD_RE = re.compile(r'(\()|(\))|(\bAND\b)|(\bOR\b)|(\bNOT\b)')

def _tokenizeQuery(s):
	tokens=[]
	pos=0
	for m in _QUERY_KEYWORD_RE.finditer(s):
		term=s[pos:m.start()].strip()
		if term:
			tokens.append(('TERM',term))
		if m.group(1):
			tokens.append(('LPAREN',None))
		elif m.group(2):
			tokens.append(('RPAREN',None))
		elif m.group(3):
			tokens.append(('AND',None))
		elif m.group(4):
			tokens.append(('OR',None))
		elif m.group(5):
			tokens.append(('NOT',None))
		pos=m.end()
	term=s[pos:].strip()
	if term:
		tokens.append(('TERM',term))
	return tokens

class _QueryParser:
	def __init__(self,tokens):
		self.tokens=tokens
		self.i=0
	def _peek(self):
		return self.tokens[self.i][0] if self.i<len(self.tokens) else None
	def _consume(self):
		t=self.tokens[self.i]
		self.i+=1
		return t
	def parseOr(self):
		left=self.parseAnd()
		while self._peek()=='OR':
			self._consume()
			right=self.parseAnd()
			left=('OR',left,right)
		return left
	def parseAnd(self):
		left=self.parseNot()
		while self._peek()=='AND':
			self._consume()
			right=self.parseNot()
			left=('AND',left,right)
		return left
	def parseNot(self):
		if self._peek()=='NOT':
			self._consume()
			return ('NOT',self.parseNot())
		return self.parseAtom()
	def parseAtom(self):
		if self._peek()=='LPAREN':
			self._consume()
			node=self.parseOr()
			if self._peek()=='RPAREN':
				self._consume()
			return node
		if self._peek()=='TERM':
			_,val=self._consume()
			return ('TERM',val)
		return None

def parseSearchQuery(name):
	# Parse a query supporting AND, OR, NOT (uppercase), and parenthesized groups.
	# Term values are lowercased for case-insensitive substring matching.
	tokens=_tokenizeQuery(name)
	if not tokens:
		return None
	tokens=[(k,v.lower()) if k=='TERM' else (k,v) for k,v in tokens]
	return _QueryParser(tokens).parseOr()

def applyAliasesToQuery(node,hero):
	if node is None:
		return None
	kind=node[0]
	if kind=='TERM':
		return ('TERM',abilityAliases(hero,node[1]))
	if kind in ('AND','OR'):
		return (kind,applyAliasesToQuery(node[1],hero),applyAliasesToQuery(node[2],hero))
	if kind=='NOT':
		return ('NOT',applyAliasesToQuery(node[1],hero))
	return node

def evalSearchQuery(node,item,deep):
	if node is None:
		return False
	kind=node[0]
	if kind=='TERM':
		return bool(deepAndShallowSearchFoundBool(item,node[1],deep))
	if kind=='AND':
		return evalSearchQuery(node[1],item,deep) and evalSearchQuery(node[2],item,deep)
	if kind=='OR':
		return evalSearchQuery(node[1],item,deep) or evalSearchQuery(node[2],item,deep)
	if kind=='NOT':
		return not evalSearchQuery(node[1],item,deep)
	return False

def collectHighlightTerms(node):
	# Terms not under a NOT, used to underline matches in the output.
	if node is None:
		return []
	kind=node[0]
	if kind=='TERM':
		return [node[1]]
	if kind in ('AND','OR'):
		return collectHighlightTerms(node[1])+collectHighlightTerms(node[2])
	return []

async def printSearch(abilities, talents, name, hero, deep=False):#Prints abilities and talents matching a boolean query
	name=name.replace('{','[').replace('}',']')#Search hotkeys/talent tiers
	if not name:
		return
	query=parseSearchQuery(name)
	if query is None:
		return
	query=applyAliasesToQuery(query,hero)
	highlights=collectHighlightTerms(query)
	output=''
	for ability in abilities:
		if evalSearchQuery(query,ability,deep):
			output+=await addUnderscoresAndNewline(highlights,ability)
	levelTiers=[0,1,2,3,4,5,6]
	if hero=='Varian':
		del levelTiers[1]
	elif hero in ['Tracer','Deathwing']:
		pass
	else:
		del levelTiers[3]
	for i in levelTiers:
		talentTier=talents[i]
		for talent in talentTier:
			if evalSearchQuery(query,talent,deep):
				output+=await addUnderscoresAndNewline(highlights,talent)
	return output

async def printLarge(channel,inputstring,separator='\n'):#Get long string. Print lines out in 2000 character chunks
	strings=[i+separator for i in inputstring.split(separator)]
	
	output=strings.pop(0)
	i=0
	j=0
	while strings:
		if i==4:#Don't make a long call in #probius hog all the bandwidth
			i=0
			await asyncio.sleep(5)
		if len(output)+len(strings[0])<2000:
			output+=strings.pop(0)
		else:
			i+=1
			if j==0:
				firstMessage=await channel.send(output)
				j=1
			else:
				await channel.send(output)
			output=strings.pop(0)
	if j==0:
		firstMessage=await channel.send(output)
	else:
		await channel.send(output)
	return firstMessage

async def printAll(client,message,keyword, deep=False, heroList=getHeroes()):#When someone calls [all/keyword]
	from heroesTalents import get_hero_data
	toPrint=''
	for hero in heroList:
		try:
			(abilities,talents)=await get_hero_data(hero)
		except FileNotFoundError:
			continue
		output=await printSearch(abilities,talents,keyword,hero,deep)
		if output=='':
			continue
		toPrint+='`'+hero.replace('_',' ')+':` '+output
	if toPrint=='':
		return
	if len(toPrint)>2000 and message.channel.guild.name in client.botChannels:#If the results is over one message, it gets dumped in specified bot channel
		channel=message.channel.guild.get_channel(client.botChannels[message.channel.guild.name])
		if channel==message.channel:#Already in #probius
			await printLarge(channel,toPrint)
		else:#Guild has a botchannel, the message was posted outside it
			introText=message.author.mention+'\n'+'Back to discussion: '+message.jump_url+'\n'
			toPrint=introText+toPrint
			redirectMessage=await message.channel.send('Sending large message in '+channel.mention+'...')
			firstMessage=await printLarge(channel,toPrint)
			await redirectMessage.edit(content=redirectMessage.content+'\n'+firstMessage.jump_url)
	else:#No bot channel
		await printLarge(message.channel,toPrint)

if __name__ == '__main__':
	from heroPage import heroAbilitiesAndTalents

	output=[]
	for hero in getHeroes():
		[abilities,talents]=heroAbilitiesAndTalents(hero)
		abilities=extraD(abilities,hero)
		for ability in abilities:
			if 'Quest' in ability:
				output.append(ability.split(':** ')[0])
	for i in output:
		print(i)

async def printEverything(client,message,abilities,talents):
	output=message.author.mention+'\n'+'\n'.join(abilities)+'\n'
	output+='\n'.join(talent for tier in talents for talent in tier)
	try:
		outputChannel=client.get_channel(client.botChannels[message.channel.guild.name])
	except:
		outputChannel=message.channel
	await printLarge(outputChannel,output)