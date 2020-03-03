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

def emit_mitigation_bullet(mitigation):
	mitigation_title = get_node_reference_title(mitigation)
	print("\n* %s" % mitigation_title.replace("Mitigation: ",''))

def do_each_attackvector(node, nodes_context, nodes_lookup):
	def collect_attack_vectors(node, parent):
		global attack_vector_collection

		if is_attack_vector(node) and (not is_outofscope(node)):
			attack_vector_collection.append(node)

		return

	collect_attack_vectors(node, None)

	do_each_once_with_deref(node, None, collect_attack_vectors, nodes_lookup)
	return

def collect_unique_mitigations(root_node, nodes_lookup):
	mitigations_table = dict()
	def collect_mitigations_by_title(node, parent):
		if not is_mitigation(node):
		    return

		target_node = node
		if is_node_a_reference(target_node):
		    target_node = get_node_referent(target_node)
		mitigation_title = get_node_reference_title(target_node)

		if mitigations_table.get(mitigation_title, None) is None:
		    mitigations_table.update({ mitigation_title: target_node })

		return

	do_each_once_with_deref(root_node, None, collect_mitigations_by_title, nodes_lookup)
	return mitigations_table.values()

def collect_mitigation_to_vector_table(node, nodes_lookup):
	mitigation_to_vector_table = dict()
	def collect_mitigation_to_vector(node, parent):
		if not is_mitigation(node):
		    return

		target_node = node
		if is_node_a_reference(target_node):
		    target_node = get_node_referent(target_node)
		mitigation_title = get_node_reference_title(target_node)

		if mitigation_to_vector_table.get(mitigation_title, None) is None:
		    mitigation_to_vector_table.update({ mitigation_title: dict() })

		mitigation_to_vector_table.get(mitigation_title).update({ get_node_title(parent) : parent.get('attr').get('evita_apt') })
		return

	do_each_once_with_deref(node, None, collect_mitigation_to_vector, nodes_lookup)
	return mitigation_to_vector_table

def do_each_riskpoint(node, nodes_lookup):
	riskpoint_node = None
	if is_riskpoint(node):
		description_lines = get_description(node).splitlines()
		if len(description_lines) > 0:
			description = description_lines[0]
			print("\nRecall: %s" % description)

		print("\nBelow is a table summarizing the risks derived from the attack tree analysis, where risk is calculated from the severities ascribed, and the likelihood of compromise is calculated from the attack tree.\n")
		print("\n\n| Attack Method | Safety Risk | Privacy Risk | Financial Risk | Operational Risk | Combined Attack Probability |")
		print("|-----------------|-------------|--------------|----------------|------------------|-----------------------------|")
		riskpoint_node = node
		emit_riskpoint_row(riskpoint_node)

		print("\n\n The following is a list of all mitigations recommended in the context of this attacker objective. They are sorted by their global risk impact score, with highest impact first.")
		mitigations = collect_unique_mitigations(node, nodes_lookup)

		for mitigation in mitigations:
			emit_mitigation_bullet(mitigation)

	for child in get_node_children(node):
		do_each_riskpoint(child, nodes_lookup)

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

garnish_apts(root_node)
apply_each_node(root_node, remove_override_apt)
propagate_all_the_apts(root_node, nodes_lookup)
derive_node_risks(root_node)
initial_risks_table = build_risks_table(root_node)

all_mitigations = collect_unique_mitigations(root_node, nodes_lookup)
for mitigation in all_mitigations:
	risk_impact_score = derive_mitigation_impact(root_node, nodes_lookup, [ mitigation ], initial_risks_table)
	risk_impact_score = int(risk_impact_score)
	if mitigation.get('attr', None) is None:
		mitigation.update({ 'attr', dict() })
	mitigation.get('attr').update({'risk_impact_score': risk_impact_score})

all_mitigations=sorted(all_mitigations, key=lambda t: float(t.get('attr').get('risk_impact_score')), reverse=True)

print("\n\n# EVITA Risk Analysis: Mitigations Priority")
print("\nIn this section, we will list every mitigation placed on any of the nodes in the attack tree. In the *Attacker Methods* sections above, these mitigations were referenced at least once, and those cases above represent the context of where each mitigation could yield its defense. Here we will present an estimate of the impact of each of the mitigations; we will estimate this impact by considering how much change in risk a given mitigation could realize in our attack tree model if the mitigation were perfectly robust, i.e., if that mitigation stopped the attack vector to which it was attached perfectly (reducing the probability of an attacker successfully using that vector to 0). We model this impact, for the purposes of prioritizing the mitigations via a sort, as a 'score' which we calculate as the product of the improvement in risk and the original risk. The risk is an EVITA risk which can range from 1-6; hence, the improvement could range from 0-5. To prioritize those mitigations with the most impact across all the attacker objectives that are in-scope, we sum all these scores and use that sum as an estimate of impact.")
print("\nNote that there will be mitigations that are found to have a zero impact. This implies only that these mitigations do not effectively work to reduce risk when deployed in isolation from other mitigations (as far as the modelling of the attacks is concerned). There may very well be combinations of these zero-impact mitigations that could also yield non-zero reduction in risk -- especially when chosen judiciously with respect to the model. For the sake of brevity, this analysis does not consider any pairwise (or greater) combinations of mitigations. Note that, as per EVITA, the list of these mitigations can also be considered to be a list of Security Requirements for the systems being analyzed.")

#TODO: report the risk impact 'class' instead of the sum
print("\n\n| Mitigation | Risk Impact Sum of Scores |")
print("|----------------------------------------------------------------------------------|-----------------------------|")
for mitigation in all_mitigations:
	print("| %s | %s |" % (get_node_reference_title(mitigation).replace('Mitigation: ', '') , mitigation.get('attr').get('risk_impact_score')) )

print("\n\n# Mitigations Details")
print("\nHere we include the descriptions for each mitigation where we determined additional details were warranted. There are some mitigations that we believed were sufficiently described by the title, previous similar mitigations or by the contexts where thy have been referenced in the trees -- for these mitigations we did not include a subsection in the following.")
for mitigation in all_mitigations:
	if node_has_description(mitigation):
		print("\n## Mitigation %s" % get_node_title(mitigation).replace('Mitigation: ', ''))
		print("\n%s" % get_description(mitigation))

garnish_apts(root_node)
apply_each_node(root_node, remove_override_apt)
propagate_all_the_apts(root_node, nodes_lookup)
derive_node_risks(root_node)

if len(objectives) > 1:
	print("\n\n# EVITA Risk Analysis: Per-Objective Mitigation Lists")
	print("\n In this section, we will list the mitigations that are relevant for each attacker objective, in turn. By 'relevant' we mean those mitigations that were found to be attached to any attack vectors underneath the attacker objective in the attack trees -- including subtrees, which are included-by-reference. The mitigations here are listed again in priority order, keeping the same global impact as previously discussed. This has the desirable effect of showing which mitigations are most useful for stopping a given attacker objective while simultaneously keeping those mitigations that will have the highest overall return-on-investment at the top of the list.")
	for objective in objectives:
		if not is_outofscope(objective):
			print("\n\n### Mitigations for Attacker Objective Node %s" % get_node_title(objective))
			objective_node = objective
			do_each_riskpoint(objective, nodes_lookup)

