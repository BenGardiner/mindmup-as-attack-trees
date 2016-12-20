#!/usr/bin/env python
from __future__ import print_function

import sys,json
import html2text
from bs4 import BeautifulSoup
import re
from collections import OrderedDict
import math
import ipdb

def info(type, value, tb):
	ipdb.pm()

sys.excepthook = info

text_maker = html2text.HTML2Text()
text_maker.body_width = 0 #disable random line-wrapping from html2text

levels_count = dict()
nodes_lookup = dict()
fixups_queue = list()
objective_node = None

def get_node_children(node):
	return OrderedDict(sorted(node.get('ideas', dict()).iteritems(), key=lambda t: float(t[0]))).values()

def is_node_a_leaf(node):
	return len(get_node_children(node)) == 0

def get_raw_description(node):
	#prefer the mindmup 2.0 'note' to the 1.0 'attachment'
	description = node.get('attr', dict()).get('note', dict()).get('text', '')
	if description is '':
		description = node.get('attr', dict()).get('attachment', dict()).get('content', '')

	return description

def detect_html(text):
	return bool(BeautifulSoup(text, "html.parser").find())

def get_description(node):
	global text_maker

	description = get_raw_description(node)

	if detect_html(description):
		description = text_maker.handle(description)

	return description

def parse_evita_raps(node):
	if not 'EVITA::' in get_raw_description(node):
		raise ValueError("couldn't find EVITA:: tag in leaf node", node)

	for line in get_description(node).splitlines():
		if not 'EVITA::' in line:
			continue

		evita_line = line.strip().split('|')

		if node.get('attr', None) is None:
		    node.update({'attr': dict()})

		attr = node.get('attr')

		attr.update({'evita_et': float(evita_line[5])})
		attr.update({'evita_e': float(evita_line[6])})
		attr.update({'evita_k': float(evita_line[7])})
		attr.update({'evita_wo': float(evita_line[8])})
		attr.update({'evita_eq': float(evita_line[9])})

	return

def derive_evita_apt(node):
	attrs = node.get('attr')

	total_rap = attrs.get('evita_et') + attrs.get('evita_e') + attrs.get('evita_k') + attrs.get('evita_wo') + attrs.get('evita_eq')
	if total_rap < 0:
		raise ValueError('encountered negative Total Required Attack Potential', node.get('attr'))
	elif total_rap < 10:
		apt = 5
	elif total_rap < 14:
		apt = 4
	elif total_rap < 20:
		apt = 3
	elif total_rap < 25:
		apt = 2
	else:
		apt = 1
	#TODO support non-zero controllability

	attrs.update({'evita_apt': apt})
	return

def parse_evita_severities(node):
	if not 'EVITA::' in get_raw_description(node):
		raise ValueError("couldn't find EVITA:: tag in leaf node", node)

	for line in get_description(node).splitlines():
		if not 'EVITA::' in line:
			continue

		evita_line = line.strip().split('|')
		attr = node.get('attr')

		attr.update({'evita_fs': float(evita_line[1])})
		attr.update({'evita_os': float(evita_line[2])})
		attr.update({'evita_ps': float(evita_line[3])})
		attr.update({'evita_ss': float(evita_line[4])})

	return

evita_security_risk_table=[
	[0,0,0,0,0],
	[0,0,1,2,3],
	[0,1,2,3,4],
	[1,2,3,4,5],
	[2,3,4,5,6]
]
def get_evita_security_risk_level(non_safety_severity, combined_attack_probability):
	global evita_security_risk_table

	if non_safety_severity < 0 or non_safety_severity > 4:
		raise ValueError('encountered an invalid non-safety severity', non_safety_severity)
	return evita_security_risk_table[int(non_safety_severity)][int(combined_attack_probability)-1]

def derive_evita_risks(this_node, objective_node):
	these_attrs = this_node.get('attr')
	objective_attrs = objective_node.get('attr')

	these_attrs.update({'evita_fr': get_evita_security_risk_level(objective_attrs.get('evita_fs'), these_attrs.get('evita_apt'))})
	these_attrs.update({'evita_or': get_evita_security_risk_level(objective_attrs.get('evita_os'), these_attrs.get('evita_apt'))})
	these_attrs.update({'evita_pr': get_evita_security_risk_level(objective_attrs.get('evita_ps'), these_attrs.get('evita_apt'))})
	these_attrs.update({'evita_sr': get_evita_security_risk_level(objective_attrs.get('evita_ss'), these_attrs.get('evita_apt'))})
	return

def is_objective(node):
	raw_description = get_raw_description(node)
	return 'OBJECTIVE::' in raw_description

def is_riskpoint(node):
	raw_description = get_raw_description(node)
	return 'RISK_HERE::' in raw_description

def do_children_firstpass(node):
	for child in get_node_children(node):
		do_node_firstpass(child)
	return

def do_node_firstpass(node):
	global nodes_lookup

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
	apt = get_node_apt(node)
	return (not apt is None) and (not math.isnan(apt)) and (not math.isinf(apt))

def update_node_apt(node, apt):
	if node.get('attr', None) is None:
		node.update({'attr': dict()})
	
	node.get('attr').update({'evita_apt': apt})

def pos_infs_of_children(node):
	for child in get_node_children(node):
		if get_node_apt(child) == float('-inf'):
			update_node_apt(child, float('inf'))

def neg_infs_of_children(node):
	for child in get_node_children(node):
		if get_node_apt(child) == float('inf'):
			update_node_apt(child, float('-inf'))

def get_max_apt_of_children(node):
	child_maximum = float('-inf')

	for child in get_node_children(node):
		child_maximum = max(child_maximum, get_node_apt(child))
	
	return child_maximum

def get_min_apt_of_children(node):
	child_minimum = float('inf')

	for child in get_node_children(node):
		child_minimum = min(child_minimum, get_node_apt(child))

	return child_minimum

def get_node_apt(node):
	return node.get('attr', dict()).get('evita_apt', None)

def get_node_referent(node, nodes_lookup):
	node_referent_title = get_node_referent_title(node)
	node_referent = nodes_lookup.get(node_referent_title, None)

	if node_referent is None:
		raise ValueError("ERROR missing node referent: %s" % node_referent_title)
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

	update_node_apt(node, float('nan'))

	if is_node_a_reference(node):
		node_referent = get_node_referent(node, nodes_lookup)
		node_referent_title=get_node_title(node_referent)

		if (not get_node_apt(node_referent) is None) and (math.isnan(get_node_apt(node_referent))):
			#is referent in-progress? then we have a loop. update the reference node with the identity of the tree reduction operation and return
			update_node_apt(node, float('-inf'))
		else:
			#otherwise, descend through referent's children

			#do all on the referent and copy the node apt back
			do_node_secondpass(node_referent, nodes_context)

			update_node_apt(node,get_node_apt(node_referent))
	else:
		if is_node_a_leaf(node):
			parse_evita_raps(node)
			derive_evita_apt(node)

		else:
			nodes_context.append(get_node_title(node))
			do_children_secondpass(node, nodes_context)
			nodes_context.pop()

			if node.get('title', None) == 'AND':
				pos_infs_of_children(node)
				update_node_apt(node, get_min_apt_of_children(node))
			else:
				neg_infs_of_children(node)
				update_node_apt(node, get_max_apt_of_children(node))

	if math.isinf(get_node_apt(node)):
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
		raise ValueError("ERROR couldn't resolve remaining infs %s" % fixups_queue)
		break
	else:
		fixups_len = len(fixups_queue)

def do_children_riskspass(node, nodes_context):
	for child in get_node_children(node):
		do_node_riskspass(child, nodes_context)
	return

def do_node_riskspass(node, nodes_context):
	global nodes_lookup
	global objective_node

	saved_objective = objective_node
	if is_objective(node):
		parse_evita_severities(node)
		objective_node = node

	if is_riskpoint(node):
		derive_evita_risks(node, objective_node)
		return

	do_children_riskspass(node, nodes_context)
	objective_node = saved_objective

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

nodes_context=list()

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data

do_children_firstpass(root_node)
do_node_secondpass(root_node, nodes_context)
do_fixups(nodes_context)
do_node_riskspass(root_node, nodes_context)

str = json.dumps(data, indent=2, sort_keys=True)
str = re.sub(r'\s+$', '', str, 0, re.M)
str = re.sub(r'\s+$', '', str, flags=re.M)

fd_out.write(str)

if len(sys.argv) >= 1:
	fd_out.close()

