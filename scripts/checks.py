#!/usr/bin/env python
from __future__ import print_function
from mindmup_as_attack_trees import *
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

def do_children_firstpass(node):
	for child in get_node_children(node):
		do_node_firstpass(child)
	return

def do_node_firstpass(node):
	global nodes_lookup

	do_children_firstpass(node)

	node_title = node.get('title', '')

	if not node_title.find('TODO') == -1 or not get_raw_description(node).find('TODO') == -1:
		print("WARNING todo node: %s" % node_title)
		return

	if node_title == 'AND' or node_title == 'OR':
		return

	if is_node_a_reference(node):
		if not is_node_a_leaf(node):
			print("ERROR reference node with children: %s" % node_title)
		return

	if nodes_lookup.get(node_title, None) is None:
		nodes_lookup.update({node_title: node})
	else:
		print("ERROR duplicate node found: %s" % node_title)

	if (not is_node_a_reference(node)) and is_attack_vector(node) and get_raw_description(node).find('EVITA::') == -1:
		print("ERROR attack vector node is missing RAP assignment: %s" % node_title)

	if (not is_node_a_reference(node)) and is_attack_vector(node) and (not get_raw_description(node).find('EVITA:: |0|0|0|0|0|0|0|0|0') == -1) and (not is_outofscope(node)):
		print("ERROR attack vector node is in-scope and has trivial RAP: %s" % node_title)

	if (not is_node_a_reference(node)) and is_attack_vector(node):
		mitigations = collect_all(node, is_mitigation)
		if len(mitigations) == 0:
			print("WARNING attack vector node has no mitigations: %s" % node_title)

	if is_objective(node) and (not is_outofscope(node)) and get_raw_description(node).find('EVITA::') == -1:
		print("ERROR Objective node w/o EVITA:: marker: %s" % node_title)

	#TODO WARNING Node with explicit (Out of Scope) label

	#TODO ERROR OBJECTIVE Node without EVITA

	#TODO ERROR EVITA:: without enough (terminated) elements of the vector (e.g. missing | terminator on last column)

	#TODO ERROR no RISK_HERE:: node

	#TODO Warn on reference to non subtree-root node (to ensure that re-used nodes are sufficiently abstracted to be their own section
	return

def is_node_weighted(node):
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

def do_children_secondpass(node, nodes_context):
	for child in get_node_children(node):
		do_node_secondpass(child, nodes_context)
	return

objective_context = None

def do_node_secondpass(node, nodes_context):
	global nodes_lookup
	global fixups_queue
	global objective_context

	if is_node_weighted(node):
		return

	update_node_weight(node, float('nan'))

	if is_objective(node):
	    objective_context = node

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
		if is_attack_vector(node):
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
					print("ERROR NaN propagating through weights at node: %s (%s)" % (get_node_title(node),nodes_context))

	if (not is_mitigation(node)) and (not is_outofscope(node)) and (not objective_context is None) and math.isinf(get_node_weight(node)):
		fixups_queue.append(node)

	if is_objective(node):
	    objective_context = None

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
	global objective_context

	if is_objective(node):
	    objective_context = node

	if not is_attack_vector(node):
		nodes_context.append(get_node_title(node))
		do_children_checkinfs(node, nodes_context)
		nodes_context.pop()

	if math.isinf(get_node_weight(node)) and (not is_outofscope(node)) and (not is_mitigation(node)) and (not objective_context is None):
		print("ERROR leftover %s at %s" % (get_node_weight(node), get_node_title(node)))

	if is_objective(node):
	    objective_context = None

	return

if len(sys.argv) < 2:
	fd_in=sys.stdin
else:
	fd_in=open(sys.argv[1], 'r')

data = json.load(fd_in)
fd_in.close()

nodes_context=list()

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data

def remove_hidden(node):
	for child in get_node_children(node):
		if get_node_title(child) == '.hidden':
			remove_child(node, child)
	return

apply_each_node(root_node, remove_hidden)

do_children_firstpass(root_node)
do_node_secondpass(root_node, nodes_context)
top_weight = get_node_weight(root_node)
#TODO check for any leftover infs and fix 'em
do_fixups(nodes_context)
do_node_checkinfs(root_node, nodes_context)

if top_weight != 0:
	print("ERROR: weights not propagated correctly through tree. Expecting 0. Got %s" % top_weight)

#TODO: check for missing referents of mitigations too
