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
parser.add_argument('subtree_name', nargs='?', help="name of the subtree root to extract")
args = parser.parse_args()

#import ipdb
def info(type, value, tb):
	ipdb.pm()

sys.excepthook = info

if args.mupin is None:
	fd_in=sys.stdin
else:
	fd_in=open(args.mupin, 'r')

data = json.load(fd_in)

fd_out = sys.stdout
fd_in.close()

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data

subtree_root = extract_subtree(root_node, args.subtree_name)

normalize_nodes(subtree_root)
str = json.dumps(subtree_root, indent=2, sort_keys=False)
str = re.sub(r'\s+$', '', str, 0, re.M)
str = re.sub(r'\s+$', '', str, flags=re.M)

fd_out.write(str)

