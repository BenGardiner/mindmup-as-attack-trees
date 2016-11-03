#!/usr/bin/env python

import sys,json
import copy

tops = list()

def truncate(node, cuts, first):
	if not first and is_cut(node.get('title',''), cuts) and 'ideas' in node:
		if not 'attr' in node:
			node.update({'attr': dict()})
		node['attr'].update({'collapsed': True})

	for key, value in node.get('ideas', dict()).iteritems():
		truncate(value, cuts, False)

	return node

def emit_tree_snapshot(title, node):
	global cuts
	global resources

	truncated = truncate(copy.deepcopy(node), cuts, True)

	#TODO: include also the 'theme' from the graphic
	if not resources is None:
		truncated.update({'resources': resources})

	truncated.update({'attr' : { 'theme': 'straightlines'}})

	title = title.replace("?", "_")

	f1 = open('%s.mup' % title, 'w')
	f1.write(json.dumps(truncated))
	f1.close()
	return

def do_ideas(depth, cuts, node):
	count = 1
	for key, value in iter(sorted(node.get('ideas', dict()).iteritems(), key=lambda (k,v): (float(k),v) )):
		add_label(depth+1, cuts, value)
		count = count+1
	return

def is_cut(title, cuts):
	for cut in cuts:
		if cut.endswith('.'):
			match_pattern='%s'
		else:
			match_pattern='%s '

		if title.startswith(match_pattern % cut):
			return True
	
	return False

def add_label(depth, cuts, node):
	global tops

	working_title = node.get('title', None)
	if is_cut(working_title, cuts):
		tops.append(node)
		return
	else:
		level = 2

	if node.get('title', None) == 'AND':
		do_ideas(depth, cuts, node)
		return

	if node.get('title', None) == '...':
		do_ideas(depth, cuts, node)
		return

	if not node.get('title', '').find('(*)') == -1:
		do_ideas(depth, cuts, node)
		return

	description = node.get('attr', dict()).get('attachment', dict()).get('content', '')
	print_title_headings(level, working_title)
	print_other_headings(level, description)

	collapsed = node.get('attr', dict()).get('collapsed', False)
	if not collapsed:
		do_ideas(depth, cuts, node)
	return

def print_title_headings(level,title):
	print("\n\n%s Attack Description: Node %s" % ('#' * (level), title ))

def print_other_headings(level, description):
	if not description == '':
		print("\n%s" % description)
	print("\n%s Attack Classification" % ('#' * (level+1)))
	print("\n%s Attack Threat" % ('#' * (level+1)))
	print("\n%s Suggested Mitigation" % ('#' * (level+1)))

def add_graphic(node, title):
	emit_tree_snapshot(title, node)
	print("\n![%s tree snapshot](%s.png)" % (title, title.replace("?", "_")))

def do_tops():
	global tops
	global cuts

	depth = 0
	heading_level = 1

	while len(tops) > 0:
		node = tops.pop(0)
		title = node.get('title', '')

		print_title_headings(heading_level, title)
		add_graphic(node, title)
		description = node.get('attr', dict()).get('attachment', dict()).get('content', '')
		print_other_headings(heading_level, description)

		do_ideas(depth, cuts, node)


cuts = sys.argv[1:]
data = json.load(sys.stdin)

resources = None
if 'resources' in data:
	resources = data['resources']
#TODO: theme

if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	tops.append(data['ideas']['1'])
else:
	tops.append(data)

do_tops()
