#!/usr/bin/env python
from __future__ import print_function
from mindmup_as_attack_trees import *

import sys,json
import re
from collections import OrderedDict
import math
import argparse
parser = argparse.ArgumentParser()

parser.add_argument("--only-severities", action='store_true', help="only generate markdown for the attacker objective severities, not the rest of the tree")
parser.add_argument('--safety-privacy-financial-operational', action='store_true', help="use this alternate ordering for the severities")
parser.add_argument('mupin', nargs='?', help="the mindmup file that will be processed -- transforming and augmenting the JSON")
args = parser.parse_args()

import ipdb
def info(type, value, tb):
	ipdb.pm()

sys.excepthook = info

levels_count = dict()
nodes_lookup = dict()
objective_node = None


def clamp_to_json_values(val):
	# JSON doesn't have infinities, but we can use strings as long as we convert back.
	if val == float('inf'):
		return "Infinity"
	elif val == float('-inf'):
		return "-Infinity"
	elif val == float('nan'):
		return "NaN"
	return val

def parse_evita_raps(node):
	if not 'EVITA::' in get_raw_description(node):
		raise ValueError("couldn't find EVITA:: tag in attack vector node", node)

	for line in get_unclean_description(node).splitlines():
		if not 'EVITA::' in line:
			continue

		evita_line = line.strip().split('|')

		if node.get('attr', None) is None:
			node.update({'attr': dict()})

		attr = node.get('attr')
		
		if len(evita_line) != 10:
			print ("EVITA:: tag should have exactly 9 elements in attack vector node %s where it only has %s" % (node,len(evita_line)-1))
			raise ValueError("EVITA:: tag should have exactly 9 elements in attack vector node %s where it only has %s" % (node,len(evita_line)-1))
		
		attr.update({'evita_et': clamp_to_json_values(float(evita_line[5]))})
		attr.update({'evita_e':  clamp_to_json_values(float(evita_line[6]))})
		attr.update({'evita_k':  clamp_to_json_values(float(evita_line[7]))})
		attr.update({'evita_wo': clamp_to_json_values(float(evita_line[8]))})
		attr.update({'evita_eq': clamp_to_json_values(float(evita_line[9]))})

	return

def get_evita_et_label(node):
	et = node.get('attr').get('evita_et')

	if et == 0:
		return "**0**: &lt; One Day"
	elif et == 1:
		return "**1**: &lt; One Week"
	elif et == 4:
		return "**4**: &lt; One Month"
	elif et == 10:
		return "**10**: &lt; Three Months"
	elif et == 17:
		return "**17**: &lt; Six Months"
	elif et == 19:
		return "**19**: &gt; Six Months"
	elif float(et) == float('inf'):
		return "Not Practical"
	else:
		return "%d Unknown" % et

def get_evita_e_label(node):
	e = node.get('attr').get('evita_e')

	if e == 0:
		return "**0**: Layman"
	elif e == 3:
		return "**3**: Proficient"
	elif e == 6:
		return "**6**: Expert"
	elif e == 8:
		return "**8**: Multiple Experts"
	elif float(e) == float('inf'):
		return "Not Practical"
	else:
		return "%d Unknown" % e

def get_evita_k_label(node):
	k = node.get('attr').get('evita_k')

	if k == 0:
		return "**0**: Public"
	elif k == 3:
		return "**3**: Restricted"
	elif k == 7:
		return "**7**: Sensitive"
	elif k == 11:
		return "**11**: Critical"
	elif float(k) == float('inf'):
		return "Not Practical"
	else:
		return "%d Unknown" % k

def get_evita_wo_label(node):
	wo = node.get('attr').get('evita_wo')

	if wo == 0:
		return "**0**: Unlimited"
	elif wo == 1:
		return "**1**: Easy"
	elif wo == 4:
		return "**4**: Moderate"
	elif wo == 10:
		return "**10**: Difficult"
	elif float(wo) == float('inf'):
		return "None"
	else:
		return "%d Unknown" % wo

def get_evita_eq_label(node):
	eq = node.get('attr').get('evita_eq')

	if eq == 0:
		return "**0**: Standard"
	elif eq == 4:
		return "**4**: Specialized"
	elif eq == 7:
		return "**7**: Bespoke"
	elif eq == 9:
		return "**9**: Multiple Bespoke"
	elif float(eq) == float('inf'):
		return "Not Practical"
	else:
		return "%d Unknown" % eq

def append_evita_rap_table(node):
	description = get_raw_description(node)

	if description.endswith('|'):
		print("warning. node %s. don't end node description in '|''" % get_node_title(node))

	html = detect_html(description)
	bookends = ("<div>", "</div>") if html else ('\n', '')

	update_raw_description(node, description +
		"%s%s" % bookends +
		"%s| Elapsed Time | Expertise | Knowledge | Window of Opportunity | Equipment |%s" % bookends +
		"%s|-----------------------------|-----------------------------|-----------------------------|-----------------------------|-----------------------------|%s" % bookends +
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

	total_rap = sum(map(lambda ev: float(attrs.get(ev)), ['evita_et', 'evita_e', 'evita_k', 'evita_wo', 'evita_eq']))

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
	update_node_apt_colour(node, apt)
	return

def get_evita_ss_label(node):
	ss = node.get('attr').get('evita_ss')
	ss = int(ss)

	if ss == 0:
		return "**S%s**: No injuries" % ss
	elif ss == 1:
		return "**S%s**: Light or moderate injuries" % ss
	elif ss == 2:
		return "**S%s**: Severe injuries (survival probable); light/moderate injuries for multiple vehicles" % ss
	elif ss == 3:
		return "**S%s**: Life threatening (survival uncertain) or fatal injuries; severe injuries for multiple vehicles" % ss
	elif ss == 4:
		return "**S%s**: Life threatening or fatal injuries for multiple vehicles" % ss
	else:
		return "**%d**: unknown" % ss

def get_evita_os_label(node):
	os = node.get('attr').get('evita_os')
	os = int(os)

	if os == 0:
		return "**S%s**: No impact on operational performance" % os
	elif os == 1:
		return "**S%s**: Impact not discernible to driver" % os
	elif os == 2:
		return "**S%s**: Driver aware of performance degradation; indiscernible impacts for multiple vehicles" % os
	elif os == 3:
		return "**S%s**: Significant impact on performance; noticeable impact for multiple vehicles" % os
	elif os == 4:
		return "**S%s**: Significant impact for multiple vehicles" % os
	else:
		return "**%d**: unknown" % os

def get_evita_ps_label(node):
	ps = node.get('attr').get('evita_ps')
	ps = int(ps)

	if ps == 0:
		return "**S%s**: No unauthorized access to data" % ps
	elif ps == 1:
		return "**S%s**: Anonymous data only (no specific driver of vehicle data)" % ps
	elif ps == 2:
		return "**S%s**: Identification of vehicle or driver; anonymous data for multiple vehicles" % ps
	elif ps == 3:
		return "**S%s**: Driver or vehicle tracking; identification of driver or vehicle for multiple vehicles" % ps
	elif ps == 4:
		return "**S%s**: Driver or vehicle tracking for multiple vehicles" % ps
	else:
		return "**%d**: unknown" % ps

def get_evita_fs_label(node):
	fs = node.get('attr').get('evita_fs')
	fs = int(fs)

	if fs == 0:
		return "**S%s**: No financial loss" % fs
	elif fs == 1:
		return "**S%s**: Low-level loss (~ 10EU)" % fs
	elif fs == 2:
		return "**S%s**: Moderate loss (~ 100EU); low losses for multiple vehicles" % fs
	elif fs == 3:
		return "**S%s**: Heavy loss (~ 1000EU); moderate losses for multiple vehicles" % fs
	elif fs == 4:
		return "**S%s**: Heavy losses for multiple vehicles" % fs
	else:
		return "**%d**: unknown" % fs

def append_evita_severity_table(node):
	description = get_raw_description(node)
	html = detect_html(description)

	if description.endswith('|'):
		print("warning. node %s. don't end node description in '|''" % get_node_title(node))

	bookends = ("<div>", "</div>") if html else ('\n', '')

	update_raw_description(node, get_raw_description(node) +
		"%s%s" % bookends +
		"%s| Safety Severity | Privacy Severity | Financial Severity | Operational Severity |%s" % bookends +
		"%s|-------------------------|-------------------------|-------------------------|-------------------------|%s" % bookends +
		("%s| %%s | %%s | %%s | %%s |%s" % bookends ) % (
			get_evita_ss_label(node),
			get_evita_ps_label(node),
			get_evita_fs_label(node),
			get_evita_os_label(node)
		)
	)

def parse_evita_severities(node):
	if not 'EVITA::' in get_raw_description(node):
		raise ValueError("couldn't find EVITA:: tag in attacker objective node", node)

	for line in get_unclean_description(node).splitlines():
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

def set_node_apts(node):
	def evita_rap_apt_parser_deriver(node):
		if is_attack_vector(node) and (not is_node_a_reference(node)):
			parse_evita_raps(node)
			derive_evita_apt(node)
			if not is_outofscope(node):
				append_evita_rap_table(node)
		return
	
	apply_each_node_below_objectives(node, evita_rap_apt_parser_deriver)
	return

def set_node_severities(node, nodes_context):
	if is_objective(node) and not is_outofscope(node):
		parse_evita_severities(node)
		append_evita_severity_table(node)

	for child in get_node_children(node):
		set_node_severities(child, nodes_context)
	return

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

nodes_lookup = build_nodes_lookup(root_node)

set_node_severities(root_node, nodes_context)

if not args.only_severities:
	set_node_apts(root_node)
	apply_each_node(root_node, remove_override_apt)
	propagate_all_the_apts(root_node, nodes_lookup)
	derive_node_risks(root_node)

normalize_nodes(root_node)
str = json.dumps(data, indent=2, sort_keys=False)
str = re.sub(r'\s+$', '', str, 0, re.M)
str = re.sub(r'\s+$', '', str, flags=re.M)

fd_out.write(str)

if len(sys.argv) >= 1:
	fd_out.close()

