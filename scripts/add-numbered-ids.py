#!/usr/bin/env python

import sys,json

levels_count = dict()

def do_ideas(depth, node):
	global levels_count

	if not depth in levels_count:
		levels_count.update({depth: 0})

	for key, value in iter(sorted(node.get('ideas', dict()).iteritems(), key=lambda t: float(t[0]))):
		add_label(depth+1, value)
	return

def add_label(depth, node):
	global levels_count

	do_ideas(depth, node)

	if node.get('title', None) == 'AND':
		return

	if node.get('title', None) == '...':
		return

	if not node.get('title', '').find('(*)') == -1:
		return

	working_title = "%s.%s %s" % (depth, levels_count[depth], node.get('title', None))

	levels_count[depth] += 1

	if not node.get('title', None).startswith(working_title):
		node.update({'title': working_title})
	return

depth=0

if len(sys.argv) < 2:
	fd_in=sys.stdin
else:
	fd_in=open(sys.argv[1], 'r')

data = json.load(fd_in)

if len(sys.argv) < 2:
	fd_out = sys.stdout
else:
	fd_in.close()
	fd_out=open(sys.argv[1],'w')

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	do_ideas(depth, data['ideas']['1'])
else:
	do_ideas(depth, data)

fd_out.write(json.dumps(data, indent=2, sort_keys=True))

if len(sys.argv) >= 1:
	fd_out.close()

