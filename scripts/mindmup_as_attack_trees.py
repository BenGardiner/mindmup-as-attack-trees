import sys
from collections import OrderedDict
import html2text
from bs4 import BeautifulSoup
import re
import math
import copy

text_maker = html2text.HTML2Text()
text_maker.body_width = 0 #disable random line-wrapping from html2text

def get_sorted_ideas(node):
	return OrderedDict(sorted(node.get('ideas', dict()).iteritems(), key=lambda t: float(t[0])))

def get_node_children(node):
	return get_sorted_ideas(node).values()

def remove_child(parent, node):
	children = parent.get('ideas', dict())
	for key, value in children.items():
		if value is node:
			children.pop(key)
	return

def is_node_a_leaf(node):
	#TODO: speed optimization: test the length of the unsorted .values() of 'ideas'
	return len(get_node_children(node)) == 0

def node_has_description(node):
	has_description = len(get_description(node).strip()) > 0
	return has_description

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

def set_background_color(node, webcolor):
	if not 'attr' in node:
		node.update({'attr': dict()})
	if not 'style' in node.get('attr'):
		node.get('attr').update({'style': dict()})
	node.get('attr').get('style').update({'background': webcolor})
	return

def set_collapsed_state(node, state):
	if not 'attr' in node:
		node.update({'attr': dict()})
	node.get('attr').update({'collapsed': state})
	return

def set_collapsed(node):
	set_collapsed_state(node, True)
	return

def set_expanded(node):
	set_collapsed_state(node, False)
	return

def is_collapsed(node):
	return node.get('attr', dict()).get('collapsed', False)

def is_cut(node, cuts):
	title = node.get('title','')
	for cut in cuts:
		if cut.endswith('.'):
			match_pattern='%s'
		else:
			match_pattern='%s '

		if title.startswith(match_pattern % cut):
			return True
	
	return is_objective(node) or is_subtree(node)

def is_all_children(node, predicate):
	for child in get_node_children(node):
		if not predicate(child):
		    return False
	return True

def is_attack_vector(node):
	if is_node_a_leaf(node):
	    return (not is_mitigation(node)) and (not is_objective(node))
	else:
	    return is_all_children(node, is_mitigation)

def is_objective(node):
	raw_description = get_raw_description(node)
	return 'OBJECTIVE::' in raw_description

def apply_first_each_node(root, fn):
	fn(root)
	for child in get_node_children(root):
		apply_first_each_node(child, fn)

	return

def apply_each_node(root, fn):
	for child in get_node_children(root):
		apply_each_node(child, fn)
	fn(root)

	return

def collect_all(root_node, predicate):
	res = list()
	def collector(node):
		if predicate(node):
			res.append(node)
		return
	apply_each_node(root_node, collector)

	return res

def collect_objectives(root_node):
	objectives = collect_all(root_node, is_objective)
	return objectives

def apply_each_node_below_objectives(root, fn):
	objectives = collect_objectives(root)
	for objective in objectives:
		for child in get_node_children(objective):
			apply_each_node(child, fn)

	return

def do_each_once_with_deref(node, parent, fn, nodes_lookup):
	breadcrumbs = list()
	def breadcrumber(node, parent):
		breadcrumbs.append(node)
		fn(node, parent)
		return

	__do_each_once_with_deref(node, parent, breadcrumber, nodes_lookup)

	for node in breadcrumbs:
		clear_once_with_deref(node)
	
	return

def __do_each_once_with_deref(node, parent, fn, nodes_lookup):
	if node.get('done', False):
		return
	node.update({'inprogress': True})

	if is_node_a_reference(node):
		node_referent = get_node_referent(node, nodes_lookup)

		if not node_referent.get('inprogress', False):
			do_each_once_with_deref(node_referent, parent, fn, nodes_lookup)
	else:
		if not is_node_a_leaf(node):
			for child in get_node_children(node):
				__do_each_once_with_deref(child, node, fn, nodes_lookup)

		if not node.get('done', False):
			node.update({'done': True})
			fn(node, parent)

	node.update({'inprogress': False})
	return

def clear_once_with_deref(root_node):
	root_node.update({'inprogress': False})
	root_node.update({'done': False})
	return

def is_node_not_for_lookup(node):
	node_title = get_node_title(node)

	if node_title.strip() == 'AND':
		return True

	if node_title.strip() == 'OR':
		return True

	if node_title == '...':
		return True

	return False

def build_nodes_lookup(root):
	nodes_lookup = dict()

	def collect_all_nodes(node):
		node_title = get_node_title(node)

		if is_node_not_for_lookup(node):
			return

		if is_node_a_reference(node):
			return

		if nodes_lookup.get(node_title, None) is None:
			nodes_lookup.update({node_title: node})
		return

	apply_each_node(root, collect_all_nodes)
	return nodes_lookup

def groom_forward_references(root):
	concrete_nodes_lookup = build_nodes_lookup(root)

	has_been_seen = dict()

	def maybe_swap(node):
		if is_node_not_for_lookup(node):
			return False

		if not is_node_a_reference(node):
			has_been_seen.update({get_node_title(node): node})
			return False

		node_referent_title = get_node_referent_title(node)

		if not has_been_seen.get(node_referent_title) is None:
			return False

		forward_referent = concrete_nodes_lookup.get(node_referent_title)
		if forward_referent is None:
			return False

		tmp = copy.deepcopy(node)
		
		node.clear()
		node.update(forward_referent)
		new_raw_description = get_raw_description(node) + '<div></div><div>SUBTREE::</div>'
		update_raw_description(node, new_raw_description)
		set_background_color(node, "#000080")

		forward_referent.clear()
		forward_referent.update(tmp)

		concrete_nodes_lookup.update({node_referent_title: node})
		has_been_seen.update({get_node_title(node): node})

		for child in get_node_children(node):
			apply_last_each_node(child, maybe_swap)

		return True

	def apply_last_each_node(root, fn):
		for child in get_node_children(root):
			apply_last_each_node(child, fn)
		fn(root)
		return

	apply_last_each_node(root, maybe_swap)
	return

def rectify_ids(root):
	#python 2.x closure madness
	class ctx:
		id_count = 1
	def rectify(node):
		node_id = node.get("id", None)
		if not node_id is None:
			node.update({'id': ctx.id_count})
			ctx.id_count = ctx.id_count + 1
		return

	apply_each_node(root, rectify)
	return

def extract_subtree(root, subtree_root_name):
	concrete_nodes_lookup = build_nodes_lookup(root)

	subtree_root = concrete_nodes_lookup.get(subtree_root_name)
	if subtree_root is None:
		raise ValueError("couldn't find subtree root \"%s\"" % subtree_root_name)

	def resolve(node):
		if is_node_not_for_lookup(node):
			return False

		if not is_node_a_reference(node):
			return False

		node_referent_title = get_node_referent_title(node)
		referent = concrete_nodes_lookup.get(node_referent_title)
		if referent is None:
			raise ValueError("couldn't find referent for \"%s\"" % node_referent_title)

		tmp = copy.deepcopy(node)

		node.clear()
		node.update(referent)
		if not is_node_a_leaf(node):
			set_collapsed(node)

		# one level is enough
		# for child in get_node_children(node):
		# 	apply_last_each_node(child, resolve)

		return True

	def apply_last_each_node(root, fn):
		for child in get_node_children(root):
			apply_last_each_node(child, fn)
		fn(root)
		return

	subtree_root_copy = copy.deepcopy(subtree_root)
	apply_last_each_node(subtree_root_copy, resolve)
	rectify_ids(subtree_root_copy)

	return subtree_root_copy

def dedup_with_references(root):
	has_been_seen = dict()

	def maybe_dedup(node):
		if is_node_not_for_lookup(node):
			return

		if not is_node_a_reference(node):
			if has_been_seen.get(get_node_title(node)) is None:
				has_been_seen.update({get_node_title(node): node})
				return

			node.update({'ideas': dict()})
			set_background_color(node, '#FFFFFF')
			update_raw_description(node, '')
			new_title=get_node_reference_title(node)
			set_node_title(node, new_title)

	#TODO: warn if dedup'ing the bigger subtree
	apply_first_each_node(root, maybe_dedup)
	return

def detect_html(text):
	return bool(BeautifulSoup(text, "html.parser").find())

def get_raw_description(node):
	#prefer the mindmup 2.0 'note' to the 1.0 'attachment'
	description = node.get('attr', dict()).get('note', dict()).get('text', '')
	if description is '':
		description = node.get('attr', dict()).get('attachment', dict()).get('content', '')

	description = description.encode('ascii','ignore')
	return description

def update_raw_description(node, new_description):
	note_present = not node.get('attr', dict()).get('note', dict()).get('text', '') is ''

	attachment_present = not node.get('attr', dict()).get('attachment', dict()).get('content', '') is ''

	#prefer the mindmup 2.0 'note' to the 1.0 'attachment'
	if (not note_present) and (not attachment_present):
		#fall-back to the minmup 1.0 attachment
		if node.get('attr') is None:
			node.update({'attr': dict()})
		if node.get('attr').get('attachment') is None:
			node.get('attr').update({'attachment': dict()})
		node.get('attr').get('attachment').update({'contentType': 'text/html'})
		attachment_present = True

	if note_present:
		node.get('attr').get('note').update({'text': new_description})

	if attachment_present:
		node.get('attr', dict()).get('attachment', dict()).update({'content': new_description})

	return

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

	matches = re.match(r'^(\d+\..*?)\s(.*?)$',title)
	if matches is None:
		wip_reference_title = "%s (*)" % title
	else:
		parsed_title = matches.groups()
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

def resolve_all_text_node_references(description, nodes_lookup):
	matches = re.findall(r'\*[^\s*]+(?:\s+[^\s*]+)* \(\*\)\s*\*',description)
	for match in matches:
		reference = re.sub(r'\*(.*?) \(\*\)\*', r'\1', match).strip()
		referent_node = nodes_lookup.get(reference, None)
		if not referent_node is None:
			if not referent_node.get('coords') is None:
				coords = referent_node.get('coords')
			else:
				title = get_node_title(referent_node)
				parsed_title = re.match(r'(\d+\..*?)\s(.*?)$',title).groups()
				coords = parsed_title[0]

			description = re.sub(r'\*(%s) \(\*\)\*' % re.escape(reference), r'*\1 (%s)*' % coords, description)
		else:
			sys.stderr.write('warning not resolving description reference: %s\n' % reference)
	
	return description

def is_node_weighted(node):
	apt = get_node_apt(node)
	return (not apt is None) and (not math.isnan(apt)) and (not math.isinf(apt))

def update_node_apt(node, apt):
	if node.get('attr', None) is None:
		node.update({'attr': dict()})

	node.get('attr').update({'evita_apt': apt})
	return

def get_node_apt(root_node):
	override_apt = list()
	def last_overide_getter(node):
		value = get_override_apt(node)
		if not value is None:
			override_apt.append(value)
		return
	apply_each_node(root_node, last_overide_getter)

	if len(override_apt) == 0:
		return root_node.get('attr', dict()).get('evita_apt', None)
	else:
		return override_apt[0]

def remove_node_apt(node):
	if not node.get('attr', None) is None:
		if not node.get('attr').get('evita_apt') is None:
			node.get('attr').pop('evita_apt')
	return

def get_override_apt(node):
	return node.get('attr', dict()).get('override_apt', None)

def set_override_apt(node, value):
	if node.get('attr', None) is None:
		node.update({'attr': dict()})

	node.get('attr').update({'override_apt': value})
	return

def remove_override_apt(node):
	if not node.get('attr', None) is None:
		if not node.get('attr').get('override_apt') is None:
			node.get('attr').pop('override_apt')
	return

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
		if is_mitigation(child):
			continue
		child_maximum = max(child_maximum, get_node_apt(child))
	
	return child_maximum

def get_min_apt_of_children(node):
	child_minimum = float('inf')

	for child in get_node_children(node):
		if is_mitigation(child):
		    continue
		child_minimum = min(child_minimum, get_node_apt(child))

	return child_minimum

def apt_propagator(node):
	if (not is_attack_vector(node)) and (not is_mitigation(node)):
		if node.get('title', None) == 'AND':
			pos_infs_of_children(node)
			update_node_apt(node, get_min_apt_of_children(node))
		else:
			neg_infs_of_children(node)
			update_node_apt(node, get_max_apt_of_children(node))
	return

def do_propagate_apt_without_deref(node):
	#NB: works because apply_each_... does al leaves first
	apply_each_node_below_objectives(node, apt_propagator)
	return

def do_propagate_apt_with_deref(node, nodes_lookup):
	if is_node_weighted(node):
		return

	if is_mitigation(node):
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
			do_propagate_apt_with_deref(node_referent, nodes_lookup)

			update_node_apt(node, get_node_apt(node_referent))
	else:
		for child in get_node_children(node):
			do_propagate_apt_with_deref(child, nodes_lookup)
		
		apt_propagator(node)
	return

def garnish_apts(root_node):
	def apt_garnisher(node):
		if not is_attack_vector(node):
			remove_node_apt(node)
		return

	apply_each_node(root_node, apt_garnisher)
	return

def do_count_fixups_needed(root_node):
	fixups = list()
	def fixups_counter(node):
		if (not is_mitigation(node)) and (not is_objective(node)) and math.isinf(get_node_apt(node)):
			fixups.append(node)
		return

	apply_each_node_below_objectives(root_node, fixups_counter)
	return len(fixups)

def do_fixup_apt(root_node):
	fixups_len = do_count_fixups_needed(root_node)

	def fixer_upper(node):
		if (not is_mitigation(node)) and math.isinf(get_node_apt(node)):
			do_propagate_apt_without_deref(node)
		return

	while fixups_len > 0:
		apply_each_node_below_objectives(root_node, fixer_upper)

		fixups_len_this_time = do_count_fixups_needed(root_node)
		if fixups_len_this_time >= fixups_len:
			fixups_needed = list()
			def fixups_collector(node):
				if (not is_mitigation(node)) and math.isinf(get_node_apt(node)):
					fixups_needed.append(node)
				return
			apply_each_node_below_objectives(root_node, fixups_collector)
			raise ValueError("ERROR couldn't resolve remaining infs %s" % fixups_needed)
			break
		else:
			fixups_len = fixups_len_this_time
	return

def propagate_all_the_apts(root_node, nodes_lookup):
	def propagtor_closure(node):
		do_propagate_apt_with_deref(node, nodes_lookup)
	apply_each_node_below_objectives(root_node, propagtor_closure)
	# fixup by doing propagation withough fixup on outstanding -infs
	do_fixup_apt(root_node)
	#propagate one last time for good measure
	do_propagate_apt_without_deref(root_node)
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

def build_risks_table(root_node):
	risks_table = dict()

	def risks_builder(node):
		if is_riskpoint(node) and (not is_outofscope(node)):
			title = get_node_title(node)
			objective_attrs = node.get('attr')
			risks = dict()

			risks.update({'evita_fr': objective_attrs.get('evita_fr')})
			risks.update({'evita_or': objective_attrs.get('evita_or')})
			risks.update({'evita_pr': objective_attrs.get('evita_pr')})
			risks.update({'evita_sr': objective_attrs.get('evita_sr')})

			risks_table.update({title: risks})
		return

	apply_each_node(root_node, risks_builder)
	return risks_table

#TODO: scaled difference the risks
def score_risk_impact(original_table, this_table):
	score = 0

	for title, risks in this_table.iteritems():
		for risk_key, risk_value in risks.iteritems():
			that = original_table.get(title).get(risk_key)
			score = score + ( (that - risk_value) * that )

	return score

def derive_evita_risks(this_node, objective_node):
	these_attrs = this_node.get('attr')
	objective_attrs = objective_node.get('attr')
	objective_apt = these_attrs.get('evita_apt')

	these_attrs.update({'evita_fr': get_evita_security_risk_level(objective_attrs.get('evita_fs'), objective_apt)})
	these_attrs.update({'evita_or': get_evita_security_risk_level(objective_attrs.get('evita_os'), objective_apt)})
	these_attrs.update({'evita_pr': get_evita_security_risk_level(objective_attrs.get('evita_ps'), objective_apt)})
	these_attrs.update({'evita_sr': get_evita_security_risk_level(objective_attrs.get('evita_ss'), objective_apt)})
	return

def final_propagate_up_to_objectives(root_node):
	def final_propagator(node):
		if is_objective(node) and (not is_outofscope(node)):
			apt_propagator(node)
		return

	apply_each_node(root_node, final_propagator)
	return

def derive_node_risks(root_node):
	final_propagate_up_to_objectives(root_node)

	for objective in collect_objectives(root_node):
		objective_node = objective

		def derivor(node):
			if is_riskpoint(node) and (not is_outofscope(node)):
				derive_evita_risks(node, objective_node)
			return

		apply_each_node(objective, derivor)

	return

def derive_mitigation_impact(root_node, nodes_lookup, mitigation_list, initial_risks_table):
	garnish_apts(root_node)
	apply_each_node(root_node, remove_override_apt)

	for mitigation in mitigation_list:
		mitigation_title = get_node_title(mitigation)
		#set 'override_apt' the mitigation node and also any references
		def apt_overrider(node):
			title = get_node_title(node)
			if is_node_a_reference(node):
				title = get_node_referent_title(node)

			if title == mitigation_title:
				set_override_apt(node, 1)
			return
		apply_each_node(root_node, apt_overrider)

	propagate_all_the_apts(root_node, nodes_lookup)
	derive_node_risks(root_node)
	this_risks_table = build_risks_table(root_node)

	#difference/'score' this_risks_table
	return score_risk_impact(initial_risks_table, this_risks_table)

def get_risk_label(evita_risk):
	evita_risk = int(evita_risk)
	if evita_risk == 0:
		return "R0"
	elif evita_risk == 1:
		return "R1"
	elif evita_risk == 2:
		return "R2"
	elif evita_risk == 3:
		return "R3"
	elif evita_risk == 4:
		return "R4"
	elif evita_risk == 5:
		return "R5"
	elif evita_risk == 6:
		return "R6"
	else:
		return "unknown"

def get_probability_label(evita_probability):
	if evita_probability == 1:
		return "1 Remote"
	elif evita_probability == 2:
		return "2 Unlikely"
	elif evita_probability == 3:
		return "3 Unlikely"
	elif evita_probability == 4:
		return "4 Likely"
	elif evita_probability == 5:
		return "5 Highly Likely"
	else:
		return "unknown"

def normalize_nodes(root_node):
	def fix_titles(root):
		def title_strip(node):
			title = get_node_title(node)

			if title is '':
				return

			title = re.sub(r'\n+', ' ', title)
			title = re.sub(r'\s+', ' ', title)
			title = re.sub(r'\s+$', '', title)

			set_node_title(node, title)
			return

		apply_each_node(root, title_strip)
		return

	def sort_children(node):
		if not is_node_a_leaf(node):
			node.update({ 'ideas': get_sorted_ideas(node) })
		return

	def order_children_contents(node):
		if not is_node_a_leaf(node):
			for v,child in node.get('ideas').iteritems():
				ordered_child = OrderedDict()

				if not child.get('title') is None:
					ordered_child.update({'title': child.pop('title')})

				if not child.get('attr') is None:
					ordered_attr = OrderedDict()
					if not child.get('attr').get('attachment') is None:
						ordered_attr.update({'attachment': child.get('attr').pop('attachment')})

					ordered_attr.update(child.pop('attr')) # everything else
					ordered_child.update({'attr':  ordered_attr})

				if not child.get('ideas') is None:
					ordered_child.update({'ideas': child.pop('ideas')})

				if not child.get('id') is None:
					ordered_child.update({'id': child.pop('id')})

				ordered_child.update(child) # everything else
				node.get('ideas').update({ v: ordered_child})
		return

	def remove_superfluous_members(node):
		if not node.get('attr') is None:
			if node.get('attr').get('collapsed') is False:
				node.get('attr').pop('collapsed')
			
			if not node.get('attr').get('position') is None:
				node.get('attr').pop('position')

			if not node.get('attr').get('style') is None:
				if len(node.get('attr').get('style')) == 0:
					node.get('attr').pop('style')

			if len(node.get('attr')) == 0:
				node.pop('attr')
		return

	nodes = root_node
	fix_titles(nodes)
	apply_each_node(nodes,remove_superfluous_members)
	apply_each_node(nodes, order_children_contents)
	apply_each_node(nodes, sort_children)
	return nodes
