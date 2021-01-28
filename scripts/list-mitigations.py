#!/usr/bin/env python
from __future__ import print_function
from mindmup_as_attack_trees import *

import sys,json
import re
from collections import OrderedDict
import math
import argparse
parser = argparse.ArgumentParser()

parser.add_argument('mupin', nargs='?', help="the mindmup file that will be processed -- transforming and augmenting the JSON")
args = parser.parse_args()

#import ipdb
def info(type, value, tb):
	ipdb.pm()

sys.excepthook = info

levels_count = dict()
nodes_lookup = dict()
fixups_queue = list()
objective_node = None

if args.mupin is None:
	fd_in=sys.stdin
else:
	fd_in=open(args.mupin, 'r')

data = json.load(fd_in)
fd_in.close()

nodes_context=list()

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data

list_of_mitigations = list()
def list_mitigation(node):
	global list_of_mitigations
	if is_mitigation(node) and not is_node_a_reference(node):
		list_of_mitigations.append(get_node_title(node))
	return

apply_each_node(root_node, list_mitigation)

def remove_numbers(title):
	modified_title = re.sub(r'^\d+\..*?\s', '', title)
	modified_title = re.sub(r'\(\d+\..*?\)', '(*)', modified_title)
	return modified_title

list_of_mitigations = sorted(list_of_mitigations, key=lambda t: remove_numbers(t))

for node in list_of_mitigations:
	print("%s" % node)

