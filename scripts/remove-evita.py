#!/usr/bin/env python

import sys,json
import re

def do_ideas(node):
	for key, value in iter(sorted(node.get('ideas', dict()).iteritems())):
		trim_attrs(value)
	return

def trim_attrs(node):
	do_ideas(node)

	attr = node.get('attr', dict())
	attr.pop('evita_et','')
	attr.pop('evita_e','')
	attr.pop('evita_k','')
	attr.pop('evita_wo','')
	attr.pop('evita_eq','')
	attr.pop('evita_fs','')
	attr.pop('evita_os','')
	attr.pop('evita_ps','')
	attr.pop('evita_ss','')
	attr.pop('evita_apt','')
	attr.pop('evita_fr','')
	attr.pop('evita_or','')
	attr.pop('evita_pr','')
	attr.pop('evita_sr','')
	
	if len(attr) == 0:
		node.pop('attr', '')

	return

if len(sys.argv) < 1:
	fd_in=sys.stdin
else:
	fd_in=open(sys.argv[1], 'r')

data = json.load(fd_in)

if len(sys.argv) < 1:
	fd_out = sys.stdout
else:
	fd_in.close()
	fd_out=open(sys.argv[1],'w')


if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data

trim_attrs(root_node)

str = json.dumps(data, indent=2, sort_keys=True)
str = re.sub(r'\s+$', '', str, 0, re.M)
str = re.sub(r'\s+$', '', str, flags=re.M)

fd_out.write(str)

if len(sys.argv) >= 1:
	fd_out.close()

