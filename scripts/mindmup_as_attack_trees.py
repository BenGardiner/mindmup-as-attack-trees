from collections import OrderedDict
import html2text
from bs4 import BeautifulSoup
import re

text_maker = html2text.HTML2Text()
text_maker.body_width = 0 #disable random line-wrapping from html2text

def get_node_children(node):
	return OrderedDict(sorted(node.get('ideas', dict()).iteritems(), key=lambda t: float(t[0]))).values()

def is_node_a_leaf(node):
	return len(get_node_children(node)) == 0

def get_node_title(node):
	return node.get('title', '')

def set_node_title(node, title):
	node.update({'title': title})
	return

def is_mitigation(node):
	return is_node_a_leaf(node) and ( 'Mitigation: ' in get_node_title(node) )

def is_subtree(node):
	raw_description = get_raw_description(node)
	return 'SUBTREE::' in raw_description

def is_objective(node):
	raw_description = get_raw_description(node)
	return 'OBJECTIVE::' in raw_description

def is_riskpoint(node):
	raw_description = get_raw_description(node)
	return 'RISK_HERE::' in raw_description

def is_outofscope(node):
	raw_description = get_raw_description(node)
	return ( "out of scope".lower() in raw_description.lower() ) or ( 'OUT_OF_SCOPE::' in raw_description )

def is_collapsed(node):
	return node.get('attr', dict()).get('collapsed', False)

def is_all_children(node, predicate):
	for child in get_node_children(node):
		if not predicate(child):
		    return False
	return True

def is_attack_vector(node):
	if is_node_a_leaf(node):
	    return not is_mitigation(node)
	else:
	    return is_all_children(node, is_mitigation)

def is_objective(node):
	raw_description = get_raw_description(node)
	return 'OBJECTIVE::' in raw_description

def apply_each_node(root, fn):
	for child in get_node_children(root):
		apply_each_node(child, fn)
	fn(root)

	return

def build_nodes_lookup(root):
	nodes_lookup = dict()

	def collect_all_nodes(node):
		node_title = node.get('title', '')

		if node_title.strip() == 'AND':
			return

		if node_title == '...':
			return

		if is_node_a_reference(node):
			return

		if nodes_lookup.get(node_title, None) is None:
			nodes_lookup.update({node_title: node})
		return

	apply_each_node(root, collect_all_nodes)
	return nodes_lookup

def detect_html(text):
	return bool(BeautifulSoup(text, "html.parser").find())

def get_raw_description(node):
	#prefer the mindmup 2.0 'note' to the 1.0 'attachment'
	description = node.get('attr', dict()).get('note', dict()).get('text', '')
	if description is '':
		description = node.get('attr', dict()).get('attachment', dict()).get('content', '')

	return description

def update_raw_description(node, new_description):
	#prefer the mindmup 2.0 'note' to the 1.0 'attachment'
	description = node.get('attr', dict()).get('note', dict()).get('text', '')
	if not description is '':
		node.get('attr').get('note').update({'text': new_description})
	else:
		node.get('attr', dict()).get('attachment', dict()).update({'content': new_description})

def get_unclean_description(node):
	global text_maker

	description = get_raw_description(node) + '\n'

	#TODO: convert special characters e.g. %lt => <
	if detect_html(description):
		description = text_maker.handle(description)

	return description

def get_description(node):
	description = get_unclean_description(node)

	#remove line breaks between '|' -- to preserve tables in 1.0 mindmups (that end up in multiple <div>)
	description = re.sub(r'\|\n+\|', '|\n|', description, re.M)

	#remove special tags (e.g. SUBTREE:: OBJECTIVE:: EVITA::)
	description = description.replace('SUBTREE::', '').replace('OBJECTIVE::','').replace('RISK_HERE::', '').replace('OUT_OF_SCOPE::','')

	description = re.sub(r'\nEVITA::.*\n', '\n\n', description, re.M)

	#remove trailing whitespace
	description = re.sub(r'\s+$', '\n', description, flags=re.M)

	#remove trailing newlines
	description = re.sub(r'\n+$', '', description)

	#remove leading newlines
	description = re.sub(r'^\n+', '', description)

	return description

def get_node_referent_title(node):
	title = node.get('title', '')

	if '(*)' in node.get('title'):
		wip_referent_title = title.replace('(*)','').strip()
	else:
		referent_coords = re.search(r'\((\d+\..*?)\)', title).groups()[0]
		wip_referent_title = "%s %s" % (referent_coords, re.sub(r'\(\d+\..*?\)', '', title).strip())
	return wip_referent_title

def get_node_reference_title(node):
	title = node.get('title','')
	parsed_title = re.match(r'(\d+\..*?)\s(.*?)$',title).groups()

	wip_reference_title = "%s (%s)" % (parsed_title[1], parsed_title[0])
	return wip_reference_title

def is_node_a_reference(node):
	title = node.get('title', '')

	return (not title.find('(*)') == -1) or (not re.search(r'\(\d+\..*?\)', title) is None)

def get_node_referent(node, nodes_lookup):
	node_referent_title = get_node_referent_title(node)
	node_referent = nodes_lookup.get(node_referent_title, None)

	if node_referent is None:
		print("ERROR missing node referent: %s" % node_referent_title)
		return node
	else:
		return node_referent


