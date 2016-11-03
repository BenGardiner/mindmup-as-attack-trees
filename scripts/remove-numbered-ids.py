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

if len(sys.argv) < 1:
	fd_in=sys.stdin
else:
	fd_in=open(sys.argv[1], 'r')

data = json.load(fd_in)

if len(sys.argv) < 1:
	fd_out = sys.stdout
else:
	fd_in.close()
	fd_out=open(sys.argv[1],'w')

do_ideas(data)
fd_out.write(json.dumps(data, indent=2, sort_keys=True))

if len(sys.argv) >= 1:
	fd_out.close()

