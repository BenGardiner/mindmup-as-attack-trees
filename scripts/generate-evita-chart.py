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

def emit_mitigation_bullet(riskpoint_node, mitigation_title):
	print("\n* %s" % mitigation_title)

def do_each_attackvector(node, nodes_context, nodes_lookup):
	def collect_attack_vectors(node, parent):
		global attack_vector_collection

		if is_attack_vector(node) and (not is_outofscope(node)):
			attack_vector_collection.append(node)

		return

	collect_attack_vectors(node, None)

	do_each_once_with_deref(node, None, collect_attack_vectors, nodes_lookup)
	clear_once_with_deref(node)
	return

def do_each_mitigation(node, nodes_lookup):
	def collect_mitigations(node, parent):
		global mitigation_collection
		global riskpoint_node

		if not is_mitigation(node):
		    return

		target_node = node
		if is_node_a_reference(target_node):
		    target_node = get_node_referent(target_node)
		mitigation_title = get_node_reference_title(target_node).replace("Mitigation: ",'')

		#TODO
		if mitigation_collection.get(mitigation_title, None) is None:
		    mitigation_collection.update({ mitigation_title: dict() })

		mitigation_collection.get(mitigation_title).update({ get_node_title(parent) : parent.get('attr').get('evita_apt') })
		return

	do_each_once_with_deref(node, None, collect_mitigations, nodes_lookup)
	clear_once_with_deref(node)
	return

def do_each_riskpoint(node, nodes_context, nodes_lookup):
	global riskpoint_node
	global mitigation_collection
	global root_node

	if is_riskpoint(node):
		print("\n\n| Attack Method | Safety Risk | Privacy Risk | Financial Risk | Operational Risk | Combined Attack Probability |")
		print("|-----------------|-------------|--------------|----------------|------------------|-----------------------------|")
		riskpoint_node = node
		emit_riskpoint_row(riskpoint_node)

		print("\n\n The following is a list of all mitigations recommended in the context of this attacker objective. There is no specific priority of the mitigations ascribed to the ordering here.")
		#collect all the mitigations, their riskpoints and all attack vectors to which the mitigation can be applied
		do_each_mitigation(node, nodes_lookup)

		for mitigation,vectors in mitigation_collection.iteritems():
			emit_mitigation_bullet(riskpoint_node, mitigation)


	if not is_node_a_leaf(node):
		for child in get_node_children(node):
			do_each_riskpoint(child, nodes_context, nodes_lookup)
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

nodes_lookup = build_nodes_lookup(root_node)
objectives = collect_objectives(root_node)

objective_node = None
riskpoint_node = None

propagate_all_the_apts(root_node, nodes_lookup)
derive_node_risks(root_node, nodes_context)

global mitigation_collection
#mitigation_collection = OrderedDict(dict(), key=lambda (k,v): v.get('total_risk')*100 + v.get('max_attack_probability'))
mitigation_collection = dict()

print("\n\n# EVITA Risk Analysis: Mitigations Collections")
for objective in objectives:
	if not is_outofscope(objective):
		print("\n\n### Mitigations for %s" % get_node_title(objective))
		objective_node = objective
		do_each_riskpoint(objective, nodes_context, nodes_lookup)
		mitigation_collection.clear()

