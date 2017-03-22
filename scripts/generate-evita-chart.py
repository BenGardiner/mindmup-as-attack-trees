#!/usr/bin/env python
from __future__ import print_function
from mindmup_as_attack_trees import *

import sys,json
import re
from collections import OrderedDict
import math
import copy

import ipdb
def info(type, value, tb):
	ipdb.pm()

sys.excepthook = info

levels_count = dict()
nodes_lookup = dict()

objectives = list()

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

def is_node_weigthed(node):
	weight = get_node_weight(node)
	return (not weight is None) and (not math.isnan(weight)) and (not math.isinf(weight))

def pos_infs_of_children(node):
	for child in get_node_children(node):
		if get_node_weight(child) == float('-inf'):
			update_node_weight(child, float('inf'))

def neg_infs_of_children(node):
	for child in get_node_children(node):
		if get_node_weight(child) == float('inf'):
			update_node_weight(child, float('-inf'))

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

def emit_riskpoint_row(riskpoint_node):
	print("| %s | %s | %s | %s | %s | %s |" % (
		get_node_title(riskpoint_node),
		get_risk_label(riskpoint_node.get('attr').get('evita_sr')),
		get_risk_label(riskpoint_node.get('attr').get('evita_pr')),
		get_risk_label(riskpoint_node.get('attr').get('evita_fr')),
		get_risk_label(riskpoint_node.get('attr').get('evita_or')),
		get_probability_label(riskpoint_node.get('attr').get('evita_apt'))
	))
	return

def emit_attackvector_row(riskpoint_node, node):
	print("| %s | %s |" % (
		get_node_title(node), #TODO: make this a hyperlink to the attack vector section (when !word output)
		get_probability_label(node.get('attr').get('evita_apt'))
	))
	return

def do_each_once_with_deref(node, parent, fn):
	global nodes_lookup
	global riskpoint_node

	if node.get('done', False):
		return

	node.update({'inprogress': True})

	if is_node_a_reference(node):
		node_referent = get_node_referent(node, nodes_lookup)

		if not node_referent.get('inprogress', False):
			do_each_once_with_deref(node_referent, parent, fn)
	else:
		if not is_node_a_leaf(node):
			for child in get_node_children(node):
				do_each_once_with_deref(child, node, fn)

		if not node.get('done', False):
			node.update({'done': True})
			fn(node, parent)

	node.update({'inprogress': False})
	return

def clear_once_with_deref(node):
	for child in get_node_children(node):
		clear_once_with_deref(child)

	node.update({'inprogress': False})
	node.update({'done': False})
	return

def do_each_attackvector(node,nodes_context):
	def collect_attack_vectors(node, parent):
		global attack_vector_collection

		if is_attack_vector(node) and (not is_outofscope(node)):
			attack_vector_collection.append(node)

		return

	collect_attack_vectors(node, None)

	do_each_once_with_deref(node, None, collect_attack_vectors)
	return

def do_each_mitigation(node):
	def collect_mitigations(node, parent):
		global mitigation_collection
		global riskpoint_node

		if not is_mitigation(node):
		    return

		target_node = node
		if is_node_a_reference(target_node):
		    target_node = get_node_referent(target_node)
		mitigation_title = get_node_title(target_node)

		#TODO
		if mitigation_collection.get(mitigation_title, None) is None:
		    mitigation_collection.update({ mitigation_title: dict() })

		mitigation_collection.get(mitigation_title).update({ get_node_title(parent) : parent.get('attr').get('evita_apt') })
		return

	do_each_once_with_deref(node, None, collect_mitigations)
	return

def do_children_each_riskpoint(node, nodes_context):
	for child in get_node_children(node):
		do_each_riskpoint(child, nodes_context)
	return

def do_each_riskpoint(node, nodes_context):
	global nodes_lookup
	global objective_node
	global riskpoint_node
	global attack_vector_collection
	global mitigation_collection
	global root_node

	if is_riskpoint(node):
		print("\n\n| Attack Method | Safety Risk | Privacy Risk | Financial Risk | Operational Risk | Combined Attack Probability |")
		print("|-----------------|-------------|--------------|----------------|------------------|-----------------------------|")
		riskpoint_node = node
		emit_riskpoint_row(riskpoint_node)

		print("\n\nThe following table summarizes the attack vector nodes contributing to the risks of above attack method and their Probability (derived using the EVITA method as discussed in this document). NB: these are all of the attack vectors which contribute to the risks; however, to what degree they make a contribution is borne-out of the attack tree structure so please consult that for details of how much contribution they make individually.")
		print("\n\n| Attack Vector | Attack Vector Probability |")
		print("|---------------------------------------------------------------------------------------|------------------------|")
		attack_vector_collection = list()

		do_each_attackvector(node, nodes_context)
		clear_once_with_deref(root_node)

		attack_vector_collection.sort(key=lambda node: node.get('attr').get('evita_apt'), reverse=True)
		for attack_vector in attack_vector_collection:
		    emit_attackvector_row(riskpoint_node, attack_vector)

		#collect all the mitigations, their riskpoints and all attack vectors to which the mitigation can be applied
		do_each_mitigation(node)
		clear_once_with_deref(root_node)

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

global mitigation_collection
#mitigation_collection = OrderedDict(dict(), key=lambda (k,v): v.get('total_risk')*100 + v.get('max_attack_probability'))
mitigation_collection = dict()

print("\n\n# EVITA Risk Analysis: Attack Tree Tables")
for objective in objectives:
	print("\n\n### Attack Tree Table for %s" % get_node_title(objective))
	objective_node = objective
	print("\nIn this section we will summarize the risks of all the attack methods of the objective *%s* and the attack vectors contributing to those risks (derived using the EVITA method as discussed in this document). NB: some attack methods may be the same node as the attack objective in what follows." % get_node_title(objective_node))
	do_each_riskpoint(objective, nodes_context)

print("\n\n# EVITA Risk Analysis: Security Requirements")
print("\nIn this section we will list, in priority order, all the mitigations against the attack vectors identified in the analysis. The priority order is defined by sorting first by Risk, then by *Combined Attack Probability*")
print("\nPlease note that, due to this tool feature being unimplemented, the sorting of these mitigations is not done here. Eventually it will be based on a metric of impact of each mitigation.")

#TODO: do a more robust sort based on impact of the mitigation

for mitigation,vectors in mitigation_collection.iteritems():
	print("\n\n## %s" % mitigation)
	sorted_vectors = OrderedDict(sorted(vectors.iteritems(), key= vectors.get))
	print("\n| Attack Vector | Attack Vector Probability |")
	print("|---------------------------------------------------------------------------------------|------------------------|")
	for vector_title,probability in sorted_vectors.iteritems():
		print("| %s | %s |" % (
			vector_title, #TODO: make this a hyperlink to the attack vector section (when !word output)
			get_probability_label(probability)
		))
