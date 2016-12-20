#!/usr/bin/env python
from __future__ import print_function

import sys,json
import re
from collections import OrderedDict
import math
import copy
import ipdb

def info(type, value, tb):
    ipdb.pm()

#sys.excepthook = info

levels_count = dict()
nodes_lookup = dict()

objectives = list()

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
	global objectives

	do_children_firstpass(node)

	node_title = node.get('title', '')

	if node_title == 'AND':
		return

	if node_title == '...':
		return

	if is_node_a_reference(node):
		return

	if nodes_lookup.get(node_title, None) is None:
		nodes_lookup.update({node_title: node})

	if is_objective(node):
		objectives.append(node)

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

def is_objective(node):
	raw_description = get_raw_description(node)
	return 'OBJECTIVE::' in raw_description

def is_riskpoint(node):
	raw_description = get_raw_description(node)
	return 'RISK_HERE::' in raw_description

def is_outofscope(node):
	raw_description = get_raw_description(node)
	return "out of scope".lower() in raw_description.lower()

def pos_infs_of_children(node):
	for child in get_node_children(node):
		if get_node_weight(child) == float('-inf'):
			update_node_weight(child, float('inf'))

def neg_infs_of_children(node):
	for child in get_node_children(node):
		if get_node_weight(child) == float('inf'):
			update_node_weight(child, float('-inf'))

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

def do_children_each_attackvector(node, nodes_context):
	for child in get_node_children(node):
		do_each_attackvector(child, nodes_context)
	return

def get_risk_label(evita_risk):
	evita_risk = int(evita_risk)
	if evita_risk == 0:
		return "R0"
	elif evita_risk == 1:
		return "R1"
	elif evita_risk == 2:
		return "R2"
	elif evita_risk == 3:
		return "R3"
	elif evita_risk == 4:
		return "R4"
	elif evita_risk == 5:
		return "R5"
	elif evita_risk == 6:
		return "R6"
	else:
		ipdb.set_trace()
		return "unknown"

def get_probability_label(evita_probability):
	if evita_probability == 1:
		return "1 Remote"
	elif evita_probability == 2:
		return "2 Unlikely"
	elif evita_probability == 3:
		return "3 Unlikely"
	elif evita_probability == 4:
		return "4 Likely"
	elif evita_probability == 5:
		return "5 Highly Likely"
	else:
		return "unknown"

def emit_row(riskpoint_node, node):
	print("|%s|%s|%s|%s|%s|%s|%s|%s" % (
		get_node_title(riskpoint_node),
		get_risk_label(riskpoint_node.get('attr').get('evita_sr')),
		get_risk_label(riskpoint_node.get('attr').get('evita_pr')),
		get_risk_label(riskpoint_node.get('attr').get('evita_fr')),
		get_risk_label(riskpoint_node.get('attr').get('evita_or')),
		get_probability_label(riskpoint_node.get('attr').get('evita_apt')),
		get_node_title(node),
		get_probability_label(node.get('attr').get('evita_apt'))
	))
	return

def do_each_attackvector(node, nodes_context):
	global nodes_lookup
	global objective_node
	global riskpoint_node

	if node.get('done', None) is riskpoint_node:
		return

	node.update({'inprogress': True})

	if is_node_a_reference(node):
		node_referent = get_node_referent(node, nodes_lookup)

		if node_referent.get('inprogress', None) is None:
			do_each_attackvector(node_referent, nodes_context)
	else:
		if not is_node_a_leaf(node):
			do_children_each_attackvector(node, nodes_context)
		elif not is_outofscope(node):
			if not node.get('done', None) is riskpoint_node:
				node.update({'done': riskpoint_node})
				emit_row(riskpoint_node, node)

	node.update({'inprogress': None})
	node.update({'done': riskpoint_node})
	return

def do_children_each_riskpoint(node, nodes_context):
	for child in get_node_children(node):
		do_each_riskpoint(child, nodes_context)
	return

def do_each_riskpoint(node, nodes_context):
	global nodes_lookup
	global objective_node
	global riskpoint_node

	if is_riskpoint(node):
		riskpoint_node = node

		do_each_attackvector(node, nodes_context)
		return

	if not is_node_a_leaf(node):
		do_children_each_riskpoint(node, nodes_context)
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

do_children_firstpass(root_node)

objective_node = None
riskpoint_node = None

print("\n\n# EVITA Risk Analysis: Attack Tree Tables")
for objective in objectives:
	print("\n\n### Attack Tree Table for %s" % get_node_title(objective))
	objective_node = objective
	print("\n|Attack Method|Safety Risk|Privacy Risk|Financial Risk|Operational Risk|Combined Attack Probability|Attack Vector|Attack Vector Probability|")
	print("|---------------|-----------|------------|--------------|----------------|---------------------------|-------------|-------------------------|")
	do_each_riskpoint(objective, nodes_context)

