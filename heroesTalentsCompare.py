import re
import difflib

def splitTalents(tier_output):
	parts = re.split(r'(?=\*\*\[)', tier_output)
	return [p for p in parts if p.strip()]

_talent_header_re = re.compile(r'^\*\*\[(\d+)\]\s*(.+?):\*\*')
def parse_talent_line(line: str):
	m = _talent_header_re.match(line.strip())
	if not m:
		return None, None, '', line
	level = int(m.group(1))
	name = m.group(2)
	header = f"**[{level}] {name}:**"
	body = line[len(header):]  # keep exact spacing after header
	return level, name, header, body

def fix_italic_underline(text: str) -> str:
	return re.sub(r'__\*(\d+(?:\.\d+)?)__', r'*__\1__', text)

def diffUnderline(live_str, ptr_str):
	live_words = live_str.split(' ')
	ptr_words = ptr_str.split(' ')
	matcher = difflib.SequenceMatcher(None, live_words, ptr_words)
	live_out = []
	ptr_out = []
	for tag, i1, i2, j1, j2 in matcher.get_opcodes():
		live_chunk = live_words[i1:i2]
		ptr_chunk = ptr_words[j1:j2]
		live_nonempty = [w for w in live_chunk if w.strip()]
		ptr_nonempty = [w for w in ptr_chunk if w.strip()]
		if tag == 'equal':
			live_out.extend(live_chunk)
			ptr_out.extend(ptr_chunk)
		elif tag == 'replace':
			if live_nonempty:
				live_out.append('__' + ' '.join(live_nonempty) + '__')
			else:
				live_out.extend(live_chunk)
			if ptr_nonempty:
				ptr_out.append('__' + ' '.join(ptr_nonempty) + '__')
			else:
				ptr_out.extend(ptr_chunk)
		elif tag == 'delete':
			# underline deleted words only on live side
			if live_nonempty:
				live_out.append('__' + ' '.join(live_nonempty) + '__')
			else:
				live_out.extend(live_chunk)
			# ptr side: nothing
		elif tag == 'insert':
			# underline inserted words only on PTR side
			if ptr_nonempty:
				ptr_out.append('__' + ' '.join(ptr_nonempty) + '__')
			else:
				ptr_out.extend(ptr_chunk)
			# live side: nothing
	return ' '.join(live_out), ' '.join(ptr_out)

def diffAbilityOutput(live_output: str, test_output: str):
	live_line = live_output.rstrip('\n')
	test_line = test_output.rstrip('\n')

	if ':**' in live_line and ':**' in test_line:
		live_header_key, live_body = live_line.split(':**', 1)
		test_header_key, test_body = test_line.split(':**', 1)
		header = live_header_key + ':**'
		live_display = live_line
	else:
		header = ''
		live_body = live_line
		test_body = test_line
		live_display = live_line

	_, ptr_body_diff = diffUnderline(live_body, test_body)
	ptr_body_diff = fix_italic_underline(ptr_body_diff)

	ptr_display = header + ptr_body_diff
	return live_display, ptr_display

def diffHeroicOutput(live_output: str, test_output: str):
	live_talents = splitTalents(live_output)
	ptr_talents  = splitTalents(test_output)

	def get_header(t: str):
		return t.split(':**')[0] if ':**' in t else t[:20]

	live_map = {get_header(t): t for t in live_talents}
	ptr_map  = {get_header(t): t for t in ptr_talents}

	all_headers = list(live_map.keys())
	for h in ptr_map:
		if h not in all_headers:
			all_headers.append(h)

	live_result = []
	ptr_result  = []

	for h in all_headers:
		l = live_map.get(h, '')
		p = ptr_map.get(h, '')

		if l and p:
			live_display, ptr_display = diffAbilityOutput(l, p)
			live_result.append(live_display)
			ptr_result.append(ptr_display)

		elif l and not p:
			level, name, header, _ = parse_talent_line(l)
			if header:
				ptr_result.append(f"{header} __*[Removed]*__")
			live_result.append(l)

		elif p and not l:
			ptr_result.append(p)

	live_block = '\n'.join(ln for ln in live_result if ln.strip())
	ptr_block  = '\n'.join(ln for ln in ptr_result  if ln.strip())

	return live_block, ptr_block

def diffTierWithMoves(live_talents_all, ptr_talents_all, tier_index):
	# 1) Build name->levels maps for move detection across all tiers
	live_name_to_levels = {}
	ptr_name_to_levels  = {}

	for tier_list in live_talents_all:
		for line in tier_list:
			level, name, _, _ = parse_talent_line(line)
			if name is not None:
				live_name_to_levels.setdefault(name, set()).add(level)

	for tier_list in ptr_talents_all:
		for line in tier_list:
			level, name, _, _ = parse_talent_line(line)
			if name is not None:
				ptr_name_to_levels.setdefault(name, set()).add(level)

	# 2) Extract this tier's talents, indexed by name
	live_tier_lines = live_talents_all[tier_index]
	ptr_tier_lines  = ptr_talents_all[tier_index]

	live_tier_by_name = {}
	for line in live_tier_lines:
		level, name, header, body = parse_talent_line(line)
		if name is not None:
			live_tier_by_name[name] = (level, header, body)

	ptr_tier_by_name = {}
	for line in ptr_tier_lines:
		level, name, header, body = parse_talent_line(line)
		if name is not None:
			ptr_tier_by_name[name] = (level, header, body)

	def make_header(level: int, name: str, strike: bool = False) -> str:
		base = f"[{level}] {name}:"
		if strike:
			return f"**~~{base}~~**"
		return f"**{base}**"

	# 3) Live block is just the raw live tier output
	live_block = '\n'.join(live_tier_lines)

	# 4) Build PTR block with annotations
	ptr_result_lines = []

	# 4a) Talents that existed at this tier on live
	for name, (live_level, live_header, live_body) in live_tier_by_name.items():
		if name in ptr_tier_by_name:
			ptr_level, ptr_header, ptr_body = ptr_tier_by_name[name]
			_, ptr_body_diff = diffUnderline(live_body, ptr_body)
			ptr_result_lines.append(ptr_header + ptr_body_diff)
		else:
			ptr_levels_for_name = ptr_name_to_levels.get(name, set())
			strike_header = make_header(live_level, name, strike=True)
			if ptr_levels_for_name:
				target_level = sorted(ptr_levels_for_name)[0]
				ptr_result_lines.append(
					f"{strike_header} __*[Moved to level {target_level}]*__"
				)
			else:
				ptr_result_lines.append(
					f"{strike_header} __*[Removed]*__"
				)

	# 4b) Talents that appear at this tier only on PTR
	for name, (ptr_level, ptr_header, ptr_body) in ptr_tier_by_name.items():
		if name in live_tier_by_name:
			continue
		live_levels_for_name = live_name_to_levels.get(name, set())
		if live_levels_for_name:
			source_level = sorted(live_levels_for_name)[0]
			ptr_result_lines.append(
				f"{ptr_header}{ptr_body} __*[Moved from level {source_level}]*__"
			)
		else:
			ptr_result_lines.append(ptr_header + ptr_body)

	ptr_block = '\n'.join(ptr_result_lines)

	return live_block, ptr_block

def _get_header(t: str) -> str:
	if ':**' not in t:
		return ''
	header = t.split(':**')[0]
	header = header.replace('__', '')
	return header

def _build_full_header_map(abilities, talents):
	result = {}
	for line in abilities:
		h = _get_header(line)
		if h:
			result[h] = line
	for tier_list in talents:
		for line in tier_list:
			h = _get_header(line)
			if h:
				result[h] = line
	return result

def _normalize_diff_block(text: str) -> str:
	lines = text.split('\n')
	while lines and not lines[0].strip():
		lines.pop(0)
	while lines and not lines[-1].strip():
		lines.pop()
	return '\n'.join(lines)

def format_live_ptr_block(live_v: str, ptr_v: str, live_block: str, ptr_block: str) -> str:
	live_block = _normalize_diff_block(live_block)
	ptr_block = _normalize_diff_block(ptr_block)
	return f"**Live [{live_v}]**\n{live_block}\n\n**PTR [{ptr_v}]**\n{ptr_block}"

def diffTierOutput(live_output, test_output):
	live_talents = splitTalents(live_output)
	ptr_talents  = splitTalents(test_output)

	live_map = {_get_header(t) or t[:20]: t for t in live_talents}
	ptr_map  = {_get_header(t) or t[:20]: t for t in ptr_talents}

	all_headers = list(live_map.keys())
	for h in ptr_map:
		if h not in all_headers:
			all_headers.append(h)

	live_result = []
	ptr_result  = []

	def split_header_body(t: str):
		if ':**' in t:
			header_key, rest = t.split(':**', 1)
			header = header_key + ':**'
			body   = rest
		else:
			header = ''
			body   = t
		return header, body

	for h in all_headers:
		l = live_map.get(h, '')
		p = ptr_map.get(h, '')

		if l and p:
			l = l.rstrip('\n')
			p = p.rstrip('\n')
			l_header, l_body = split_header_body(l)
			p_header, p_body = split_header_body(p)
			ld_body, pd_body = diffUnderline(l_body, p_body)
			live_result.append(l_header + ld_body)
			ptr_result.append(p_header + pd_body)

		elif l and not p:
			l = l.rstrip('\n')
			live_result.append('__' + l + '__')
			ptr_result.append('')

		elif p and not l:
			p = p.rstrip('\n')
			live_result.append('')
			ptr_result.append(p)

	live_block = '\n'.join(ln for ln in live_result if ln.strip())
	ptr_block  = '\n'.join(ln for ln in ptr_result  if ln.strip())

	return live_block, ptr_block

def diffSearchOutput(live_output: str,
					 test_output: str,
					 abilities, talents,
					 test_abilities, test_talents):
	live_full = _build_full_header_map(abilities, talents)
	ptr_full  = _build_full_header_map(test_abilities, test_talents)

	ptr_segments = splitTalents(test_output)

	ptr_result = []

	for seg in ptr_segments:
		seg = seg.rstrip('\n')
		header_key = _get_header(seg)
		if not header_key:
			ptr_result.append(seg)
			continue

		if header_key in live_full:
			l_full = live_full[header_key]
			p_full = ptr_full.get(header_key, seg)

			if ':**' in l_full and ':**' in p_full:
				l_header_key, l_body = l_full.split(':**', 1)
				p_header_key, p_body = p_full.split(':**', 1)
				header = p_header_key + ':**'

				_, ptr_body_diff = diffUnderline(l_body, p_body)
				ptr_body_diff = fix_italic_underline(ptr_body_diff)

				ptr_result.append(header + ptr_body_diff)
			else:
				_, ptr_diff = diffUnderline(l_full, p_full)
				ptr_result.append(ptr_diff)
		else:
			cleaned = re.sub(r'__([^_]+)__', r'\1', seg)
			ptr_result.append('__' + cleaned + '__')

	live_block = _normalize_diff_block(live_output)
	live_block = re.sub(r'__([^_]+)__', r'\1', live_block)

	ptr_block  = _normalize_diff_block('\n'.join(ptr_result))
	return live_block, ptr_block
