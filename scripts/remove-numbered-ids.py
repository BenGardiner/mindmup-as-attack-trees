#!/usr/bin/env python

import sys,json
import re

def do_ideas(node):
	for key, value in iter(sorted(node.get('ideas', dict()).iteritems())):
		trim_label(value)
	return

def trim_label(node):
	do_ideas(node)

	if node.get('title', None) == 'AND':
		return

	if node.get('title', None) == '...':
		return

	if not node.get('title', '').find('(*)') == -1:
		return

	node.update({'title': re.sub(r'^\d\..*?\s','',node.get('title', ''))})
	return

data = json.load(sys.stdin)
do_ideas(data)
print(json.dumps(data))

