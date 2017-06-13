#!/usr/bin/env python
from mindmup_as_attack_trees import *

import sys,json
import re
from collections import OrderedDict
import ipdb
import argparse
parser = argparse.ArgumentParser()

parser.add_argument('mupin', help="the mindmup file that will be processed -- transforming and augmenting the JSON")
args = parser.parse_args()

def info(type, value, tb):
    ipdb.pm()

sys.excepthook = info

levels_count = dict()
nodes_lookup = dict()

depth=0

fd_in=open(args.mupin, 'r')
data = json.load(fd_in)
fd_in.close()

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data

nodes_lookup = dict()

def nodes_lookup_flat_builder(node):
	node_title = node.get('title', '')

	if node_title.strip() == 'AND':
		return

	if node_title == '...':
		return

	if is_node_a_reference(node):
		return

	if nodes_lookup.get(node_title, None) is None:
		matched = re.match(r'(\d+\..*?)\s(.*?)$',node_title)
		if matched is None:
		    return

		parsed_title = matched.groups()
		
		node_title = parsed_title[1]

		nodes_lookup.update({node_title: node})
	return

apply_each_node(root_node, nodes_lookup_flat_builder)

text = sys.stdin.read()

text = resolve_all_text_node_references(text, nodes_lookup)

sys.stdout.write(text)

