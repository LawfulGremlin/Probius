import os
HARDCODED_TOKEN = ''
HARDCODED_TOKEN_FILE = ''

def getDiscordToken():
	# Tier 1: Docker
	env_val = os.environ.get('DISCORD_TOKEN')
	if env_val:
		if os.path.isfile(env_val):
			with open(env_val) as f:
				return f.read().strip()
		return env_val

	# Tier 2: Hardcoded file
	if HARDCODED_TOKEN_FILE and os.path.isfile(HARDCODED_TOKEN_FILE):
		with open(HARDCODED_TOKEN_FILE) as f:
			return f.read().strip()

	# Tier 3: Hardcoded value
	if HARDCODED_TOKEN:
		return HARDCODED_TOKEN

	raise RuntimeError(
		'No Discord token found.'
	)
