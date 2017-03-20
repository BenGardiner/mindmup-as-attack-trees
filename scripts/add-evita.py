#!/usr/bin/env python
from __future__ import print_function

import sys,json
import html2text
from bs4 import BeautifulSoup
import re
from collections import OrderedDict
import math
import ipdb
import argparse
parser = argparse.ArgumentParser()

parser.add_argument("--only-severities", action='store_true', help="only generate markdown for the attacker objective severities, not the rest of the tree")
parser.add_argument('--safety-privacy-financial-operational', action='store_true', help="use this alternate ordering for the severities")
parser.add_argument('mupin', nargs='?', help="the mindmup file that will be processed -- transforming and augmenting the JSON")
args = parser.parse_args()

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

def set_raw_description(node, new_description):
	#prefer the mindmup 2.0 'note' to the 1.0 'attachment'
	description = node.get('attr', dict()).get('note', dict()).get('text', '')
	if not description is '':
		node.get('attr').get('note').update({'text': new_description})
	else:
		node.get('attr', dict()).get('attachment', dict()).update({'content': new_description})


def detect_html(text):
	return bool(BeautifulSoup(text, "html.parser").find())

def get_description(node):
	global text_maker

	description = get_raw_description(node)

	if detect_html(description):
		description = text_maker.handle(description)

	return description

def clamp_to_json_values(val):
    return max(-1 * sys.float_info.max, min(val, sys.float_info.max))

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

		attr.update({'evita_et': clamp_to_json_values(float(evita_line[5]))})
		attr.update({'evita_e':  clamp_to_json_values(float(evita_line[6]))})
		attr.update({'evita_k':  clamp_to_json_values(float(evita_line[7]))})
		attr.update({'evita_wo': clamp_to_json_values(float(evita_line[8]))})
		attr.update({'evita_eq': clamp_to_json_values(float(evita_line[9]))})

	return

def get_evita_et_label(node):
	et = node.get('attr').get('evita_et')

	if et == 0:
		return "0 &lt; one day"
	elif et == 1:
		return "1 &lt; one week"
	elif et == 4:
		return "4 &lt; one month"
	elif et == 10:
		return "10 &lt; three months"
	elif et == 17:
		return "17 &lt; six months"
	elif et == 19:
		return "19 &gt; six months"
	elif et == float('inf'):
		return "Not Practical"
	else:
		return "%d unknown" % et

def get_evita_e_label(node):
	e = node.get('attr').get('evita_e')

	if e == 0:
		return "0 Layman"
	elif e == 3:
		return "3 Proficient"
	elif e == 6:
		return "6 Expert"
	elif e == 8:
		return "8 Multiple Experts"
	elif e == float('inf'):
		return "Not Practical"
	else:
		return "%d unknown" % e

def get_evita_k_label(node):
	k = node.get('attr').get('evita_k')

	if k == 0:
		return "0 Public"
	elif k == 3:
		return "3 Restricted"
	elif k == 7:
		return "7 Sensitive"
	elif k == 11:
		return "11 Critical"
	elif k == float('inf'):
		return "Not Practical"
	else:
		return "%d unknown" % k

def get_evita_wo_label(node):
	wo = node.get('attr').get('evita_wo')

	if wo == 0:
		return "0 Unlimited"
	elif wo == 1:
		return "1 Easy"
	elif wo == 4:
		return "4 Moderate"
	elif wo == 10:
		return "10 Difficult"
	elif wo == float('inf'):
		return "None"
	else:
		return "%d unknown" % wo

def get_evita_eq_label(node):
	eq = node.get('attr').get('evita_eq')

	if eq == 0:
		return "0 Standard"
	elif eq == 4:
		return "4 Specialized"
	elif eq == 7:
		return "7 Bespoke"
	elif eq == 9:
		return "9 Multiple Bespoke"
	elif eq == float('inf'):
		return "Not Practical"
	else:
		return "%d unknown" % eq

def append_evita_rap_table(node):
	description = get_raw_description(node)

	if description.endswith('|'):
	    print("warning. node %s. don't end node description in '|''" % get_node_title(node))

	html = detect_html(description)
	bookends = ("<div>", "</div>") if html else ('\n', '')

	set_raw_description(node, description +
		"%s%s" % bookends +
		"%s| Elapsed Time | Expertise | Knowledge | Window of Opportunity | Equipment |%s" % bookends +
		"%s|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|%s" % bookends +
		("%s| %%s | %%s | %%s | %%s | %%s |%s" % bookends ) % (
			get_evita_et_label(node),
			get_evita_e_label(node),
			get_evita_k_label(node),
			get_evita_wo_label(node),
			get_evita_eq_label(node)
		)
	)

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

def get_evita_ss_label(node):
	ss = node.get('attr').get('evita_ss')
	ss = int(ss)

	if ss == 0:
		return "S%s No injuries" % ss
	elif ss == 1:
		return "S%s Light or moderate injuries" % ss
	elif ss == 2:
		return "S%s Severe injuries (survival probable); light/moderate injuries for multiple vehicles" % ss
	elif ss == 3:
		return "S%s Life threatening (survivaluncertain) or fatal injuries; severe injuries for multiple vehicles" % ss
	elif ss == 4:
		return "S%s Life threatening or fatal in-juries for multiple vehicles" % ss
	else:
		return "%d unknown" % ss

def get_evita_os_label(node):
	os = node.get('attr').get('evita_os')
	os = int(os)

	if os == 0:
		return "S%s No impact on operational performance" % os
	elif os == 1:
		return "S%s Impact not discernible to driver" % os
	elif os == 2:
		return "S%s Driver aware of performance degradation; indiscernible impacts for multiple vehicles" % os
	elif os == 3:
		return "S%s Significant impact on performance; noticeable impact for multiple vehicles" % os
	elif os == 4:
		return "S%s Significant impact for multiple vehicles" % os
	else:
		return "%d unknown" % os

def get_evita_ps_label(node):
	ps = node.get('attr').get('evita_ps')
	ps = int(ps)

	if ps == 0:
		return "S%s No unauthorized access to data" % ps
	elif ps == 1:
		return "S%s Anonymous data only (no specific driver of vehicle data)" % ps
	elif ps == 2:
		return "S%s Identification of vehicle or driver; anonymous data for multiple vehicles" % ps
	elif ps == 3:
		return "S%s Driver or vehicle tracking; identification of driver or vehicle for multiple vehicles" % ps
	elif ps == 4:
		return "S%s Driver or vehicle tracking for multiple vehicles" % ps
	else:
		return "%d unknown" % ps

def get_evita_fs_label(node):
	fs = node.get('attr').get('evita_fs')
	fs = int(fs)

	if fs == 0:
		return "S%s No financial loss" % fs
	elif fs == 1:
		return "S%s Low-level loss (~ 10EU)" % fs
	elif fs == 2:
		return "S%s Moderate loss (~ 100EU); low losses for multiple vehicles" % fs
	elif fs == 3:
		return "S%s Heavy loss (~ 1000EU); moderate losses for multiple vehicles" % fs
	elif fs == 4:
		return "S%s Heavy losses for multiple vehicles" % fs
	else:
		return "%d unknown" % fs

def append_evita_severity_table(node):
	description = get_raw_description(node)
	html = detect_html(description)

	if description.endswith('|'):
	    print("warning. node %s. don't end node description in '|''" % get_node_title(node))

	bookends = ("<div>", "</div>") if html else ('\n', '')

	set_raw_description(node, get_raw_description(node) +
		"%s%s" % bookends +
		"%s| Safety Severity | Privacy Severity | Financial Severity | Operational Severity |%s" % bookends +
		"%s|-------------------------|-------------------------|-------------------------|-------------------------|%s" % bookends +
		("%s| %%s | %%s | %%s | %%s |%s" % bookends ) % (
			get_evita_fs_label(node),
			get_evita_os_label(node),
			get_evita_ps_label(node),
			get_evita_ss_label(node)
		)
	)

def parse_evita_severities(node):
	if not 'EVITA::' in get_raw_description(node):
		raise ValueError("couldn't find EVITA:: tag in leaf node", node)

	for line in get_description(node).splitlines():
		if not 'EVITA::' in line:
			continue

		evita_line = line.strip().split('|')
		attr = node.get('attr')

		if args.safety_privacy_financial_operational:
		    attr.update({'evita_ss': clamp_to_json_values(float(evita_line[1]))})
		    attr.update({'evita_ps': clamp_to_json_values(float(evita_line[2]))})
		    attr.update({'evita_fs': clamp_to_json_values(float(evita_line[3]))})
		    attr.update({'evita_os': clamp_to_json_values(float(evita_line[4]))})
		else:
		    attr.update({'evita_fs': clamp_to_json_values(float(evita_line[1]))})
		    attr.update({'evita_os': clamp_to_json_values(float(evita_line[2]))})
		    attr.update({'evita_ps': clamp_to_json_values(float(evita_line[3]))})
		    attr.update({'evita_ss': clamp_to_json_values(float(evita_line[4]))})

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
			append_evita_rap_table(node)

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

def do_children_thirdpass(node, nodes_context):
    for child in get_node_children(node):
	do_node_thirdpass(child, nodes_context)
    return

def do_node_thirdpass(node, nodes_context):
	global nodes_lookup
	global fixups_queue

	if not is_node_a_leaf(node):
		nodes_context.append(get_node_title(node))
		do_children_thirdpass(node, nodes_context)
		nodes_context.pop()

		if node.get('title', None) == 'AND':
			pos_infs_of_children(node)
			update_node_apt(node, get_min_apt_of_children(node))
		else:
			neg_infs_of_children(node)
			update_node_apt(node, get_max_apt_of_children(node))

	return

def do_children_severitiespass(node, nodes_context):
	for child in get_node_children(node):
		do_node_severitiespass(child, nodes_context)
	return

def do_node_severitiespass(node, nodes_context):
	if is_objective(node):
		parse_evita_severities(node)
		append_evita_severity_table(node)

	do_children_severitiespass(node, nodes_context)
	return

def do_children_riskspass(node, nodes_context):
	for child in get_node_children(node):
		do_node_riskspass(child, nodes_context)
	return

def do_node_riskspass(node, nodes_context):
	global nodes_lookup
	global objective_node

	saved_objective = objective_node
	if is_objective(node):
		objective_node = node

	if is_riskpoint(node):
		derive_evita_risks(node, objective_node)
		return

	node.get('attr').pop('evita_apt')
	do_children_riskspass(node, nodes_context)
	objective_node = saved_objective

if args.mupin is None:
	fd_in=sys.stdin
else:
	fd_in=open(args.mupin, 'r')

data = json.load(fd_in)

if args.mupin is None:
	fd_out = sys.stdout
else:
	fd_in.close()
	fd_out=open(args.mupin,'w')

nodes_context=list()

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data

do_children_firstpass(root_node)
do_node_severitiespass(root_node, nodes_context)
if not args.only_severities:
    do_node_secondpass(root_node, nodes_context)
    do_fixups(nodes_context)
    do_node_thirdpass(root_node, nodes_context)
    do_node_riskspass(root_node, nodes_context)

str = json.dumps(data, indent=2, sort_keys=True)
str = re.sub(r'\s+$', '', str, 0, re.M)
str = re.sub(r'\s+$', '', str, flags=re.M)

fd_out.write(str)

if len(sys.argv) >= 1:
	fd_out.close()

