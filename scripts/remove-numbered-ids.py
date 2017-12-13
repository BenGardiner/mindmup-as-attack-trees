#!/usr/bin/env python

import sys,json
from mindmup_as_attack_trees import *

def do_ideas(node):
	for key, value in iter(sorted(node.get('ideas', dict()).iteritems())):
		trim_label(value)
	return

def trim_label(node):
	do_ideas(node)

	if node.get('title', None) == 'AND' or node.get('title', None) == 'OR':
		return

	if node.get('title', None) == '...':
		return

	if not node.get('title', '').find('(*)') == -1:
		return

	title = node.get('title', '')
	title = re.sub(r'^\d+\..*?\s', '', title)
	title = re.sub(r'\(\d+\..*?\)', '(*)', title)

	description = get_raw_description(node)
	description = re.sub(r'\*(.*?) \(\d+\.\d+\)\*', r'*\1 (*)*', description)
	update_raw_description(node, description)

	node.update({'title': title})
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

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data
do_ideas(root_node)

normalize_nodes(root_node)
str = json.dumps(data, indent=2, sort_keys=False)
str = re.sub(r'\s+$', '', str, 0, re.M)
str = re.sub(r'\s+$', '', str, flags=re.M)

fd_out.write(str)

if len(sys.argv) >= 1:
	fd_out.close()

