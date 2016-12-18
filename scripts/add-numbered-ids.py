#!/usr/bin/env python

import sys,json
import re
from collections import OrderedDict
import ipdb

def info(type, value, tb):
    ipdb.pm()

sys.excepthook = info

levels_count = dict()
nodes_lookup = dict()

def is_node_a_reference(node):
	node_title = node.get('title', '')
	return (not node_title.find('(*)') == -1)

def get_node_referent_title(node):
	return node.get('title', '').replace('(*)','').strip()

def get_node_children(node):
	return OrderedDict(sorted(node.get('ideas', dict()).iteritems(), key=lambda t: float(t[0]))).values()

def do_ideas(depth, node):
	global levels_count

	if not depth in levels_count:
		levels_count.update({depth: 0})

	for key, value in iter(sorted(node.get('ideas', dict()).iteritems(), key=lambda t: float(t[0]))):
		add_label(depth+1, value)
	return

def add_label(depth, node):
	global levels_count
	global nodes_lookup

	do_ideas(depth, node)
	node_title = node.get('title', '')

	if node_title == 'AND':
		return

	if node_title == '...':
		return

	if is_node_a_reference(node):
		return

	node.update({'coords': "%s.%s" % (depth, levels_count[depth])})

	if nodes_lookup.get(node_title, None) is None:
		nodes_lookup.update({node_title: node})

	levels_count[depth] += 1
	return

def foreach_node_secondpass(node):
	for child in get_node_children(node):
		process_secondpass(child)
	return

def process_secondpass(node):
	global nodes_lookup

	foreach_node_secondpass(node)
	node_title = node.get('title', '')

	if node_title == 'AND':
		return

	if node_title == '...':
		return

	working_title = node.get('title', '')
	if is_node_a_reference(node):
		referent_node = nodes_lookup.get(get_node_referent_title(node), None)
		working_title = working_title.replace('(*)', '')
		working_title = "%s(%s)" % (working_title, referent_node.get('coords'))
	else:
		working_title = "%s %s" % (node.get('coords'), working_title)

	if not node.get('title', None).startswith(working_title):
		node.update({'title': working_title})
	return

def foreach_node_thirdpass(node):
	for child in get_node_children(node):
		process_thirdpass(child)
	return

def process_thirdpass(node):
	foreach_node_thirdpass(node)

	node.pop('coords', None)
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
	root_node = data['ideas']['1']
else:
	root_node = data

do_ideas(depth, root_node)
foreach_node_secondpass(root_node)
foreach_node_thirdpass(root_node)

str = json.dumps(data, indent=2, sort_keys=True)
str = re.sub(r'\s+$', '', str, 0, re.M)
str = re.sub(r'\s+$', '', str, flags=re.M)

fd_out.write(str)

if len(sys.argv) >= 1:
	fd_out.close()

