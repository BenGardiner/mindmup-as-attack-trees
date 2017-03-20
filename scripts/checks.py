#!/usr/bin/env python
from __future__ import print_function

import sys,json
import re
from collections import OrderedDict
import math
import ipdb

def info(type, value, tb):
    ipdb.pm()

#sys.excepthook = info

levels_count = dict()
nodes_lookup = dict()
fixups_queue = list()

def get_node_children(node):
	return OrderedDict(sorted(node.get('ideas', dict()).iteritems(), key=lambda t: float(t[0]))).values()

def is_node_a_leaf(node):
	return len(get_node_children(node)) == 0

def is_objective(node):
	raw_description = get_raw_description(node)
	return 'OBJECTIVE::' in raw_description

def get_raw_description(node):
	#prefer the mindmup 2.0 'note' to the 1.0 'attachment'
	description = node.get('attr', dict()).get('note', dict()).get('text', '')
	if description is '':
		description = node.get('attr', dict()).get('attachment', dict()).get('content', '')

	return description

def do_children_firstpass(node):
	for child in get_node_children(node):
		do_node_firstpass(child)
	return

def do_node_firstpass(node):
	global nodes_lookup

	do_children_firstpass(node)

	node_title = node.get('title', '')

	if not node_title.find('TODO') == -1:
		print("WARNING todo node: %s" % node_title)

	if node_title == 'AND':
		return

	if is_node_a_reference(node):
		if not is_node_a_leaf(node):
			print("ERROR reference node with children: %s" % node_title)
		return

	if nodes_lookup.get(node_title, None) is None:
		nodes_lookup.update({node_title: node})
	else:
		print("ERROR duplicate node found: %s" % node_title)

	if (not is_node_a_reference(node)) and is_node_a_leaf(node) and get_raw_description(node).find('EVITA::') == -1:
		print("ERROR leaf node w/o (complete) description text: %s" % node_title)

	if is_objective(node) and get_raw_description(node).find('EVITA::') == -1:
		print("ERROR Objective node w/o EVITA:: marker: %s" % node_title)

	#TODO ERROR Node with labeled (Out of Scope) without EVITA:: *inf*

	#TODO WARNING Node with expliciti (Out of Scope) label

	#TODO ERROR OBJECTIVE Node without EVITA

	#TODO ERROR EVITA:: without enough (terminated) elements of the vector (e.g. missing | terminator on last column)

	#TODO ERROR no RISK_HERE:: node
	return

def get_node_referent_title(node):
	title = node.get('title', '')

	if '(*)' in node.get('title'):
		wip_referent_title = title.replace('(*)','').strip()
	else:
		referent_coords = re.search(r'\((\d+\..*?)\)', title).groups()[0]
		wip_referent_title = "%s %s" % (referent_coords, re.sub(r'\(\d+\..*?\)', '', title).strip())
	return wip_referent_title

def is_node_a_reference(node):
	title = node.get('title', '')

	return (not title.find('(*)') == -1) or (not re.search(r'\(\d+\..*?\)', title) is None)

def is_node_weigthed(node):
	weight = get_node_weight(node)
	return (not weight is None) and (not math.isnan(weight)) and (not math.isinf(weight))

def update_node_weight(node, weight):
	if node.get('attr', None) is None:
		node.update({'attr': dict()})
	
	node.get('attr').update({'weight': weight})

def pos_infs_of_children(node):
	for child in get_node_children(node):
		if get_node_weight(child) == float('-inf'):
			update_node_weight(child, float('inf'))

def neg_infs_of_children(node):
	for child in get_node_children(node):
		if get_node_weight(child) == float('inf'):
			update_node_weight(child, float('-inf'))

def get_max_weight_of_children(node):
	child_maximum = float('-inf')

	for child in get_node_children(node):
		child_maximum = max(child_maximum, get_node_weight(child))
	
	return child_maximum

def get_min_weight_of_children(node):
	child_minimum = float('inf')

	for child in get_node_children(node):
		child_minimum = min(child_minimum, get_node_weight(child))
	
	return child_minimum

def get_node_weight(node):
	return node.get('attr', dict()).get('weight', None)

def get_node_referent(node, nodes_lookup):
	node_referent_title = get_node_referent_title(node)
	node_referent = nodes_lookup.get(node_referent_title, None)

	if node_referent is None:
		print("ERROR missing node referent: %s" % node_referent_title)
		return node
	else:
		return node_referent

def get_node_title(node):
	return node.get('title', '')

def do_children_secondpass(node, nodes_context):
	for child in get_node_children(node):
		do_node_secondpass(child, nodes_context)
	return

def do_node_secondpass(node, nodes_context):
	global nodes_lookup
	global fixups_queue

	if is_node_weigthed(node):
		return

	update_node_weight(node, float('nan'))

	if is_node_a_reference(node):
		node_referent = get_node_referent(node, nodes_lookup)
		node_referent_title=get_node_title(node_referent)

		if (not get_node_weight(node_referent) is None) and (math.isnan(get_node_weight(node_referent))):
			#is referent in-progress? then we have a loop. update the reference node with the identity of the tree reduction operation and return
			update_node_weight(node, float('-inf'))
		else:
			#otherwise, descend through referent's children

			#do all on the referent and copy the node weight back
			do_node_secondpass(node_referent, nodes_context)

			update_node_weight(node,get_node_weight(node_referent))
	else:
		if is_node_a_leaf(node):
			update_node_weight(node, 0)
		else:
			nodes_context.append(get_node_title(node))
			do_children_secondpass(node, nodes_context)
			nodes_context.pop()

			if node.get('title', None) == 'AND':
				pos_infs_of_children(node)
				update_node_weight(node, get_min_weight_of_children(node))
			else:
				neg_infs_of_children(node)
				update_node_weight(node, get_max_weight_of_children(node))

			if get_node_weight(node) is None:
				print("ERROR None propagating through weights at node: %s" % get_node_title(node))
			else:
				if math.isnan(get_node_weight(node)):
					print("ERROR NaN propagting through weights at node: %s (%s)" % (get_node_title(node),nodes_context))

	if math.isinf(get_node_weight(node)):
		fixups_queue.append(node)
	return

def do_fixups(nodes_context):
    global fixups_queue
    fixups_len = len(fixups_queue)

    while len(fixups_queue) > 0:
	fixups_this_time = list(fixups_queue)
	fixups_queue = list()
	for node in fixups_this_time:
		do_node_secondpass(node, nodes_context)
	
	if len(fixups_queue) >= fixups_len:
	    print("ERROR couldn't resolve remaining infs %s" % fixups_queue)
	    break
	else:
	    fixups_len = len(fixups_queue)


def do_children_checkinfs(node, nodes_context):
	for child in get_node_children(node):
		do_node_checkinfs(child, nodes_context)
	return

def do_node_checkinfs(node, nodes_context):
	if not is_node_a_leaf(node):
	    nodes_context.append(get_node_title(node))
	    do_children_checkinfs(node, nodes_context)
	    nodes_context.pop()

	if math.isinf(get_node_weight(node)):
		print("ERROR leftover %s at %s" % (get_node_weight(node), get_node_title(node)))

if len(sys.argv) < 2:
	fd_in=sys.stdin
else:
	fd_in=open(sys.argv[1], 'r')

data = json.load(fd_in)
fd_in.close()

nodes_context=list()

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	do_children_firstpass(data['ideas']['1'])
	do_node_secondpass(data['ideas']['1'], nodes_context)
	top_weight = get_node_weight(data['ideas']['1'])
	#TODO check for any leftover infs and fix 'em
	do_fixups(nodes_context)
	do_node_checkinfs(data['ideas']['1'], nodes_context)
else:
	do_children_firstpass(data)
	do_node_secondpass(data, nodes_context)
	top_weight = get_node_weight(data)
	#TODO check for any leftover infs and fix 'em
	do_fixups(nodes_context)
	do_node_checkinfs(data, nodes_context)

if top_weight != 0:
	print("ERROR: weights not propagated correctly through tree. Expecting 0. Got %s" % top_weight)
