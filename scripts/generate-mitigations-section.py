
if 'id' in data and data['id'] == 'root':
	#version 2 mindmup
	root_node = data['ideas']['1']
else:
	root_node = data

nodes_lookup = build_nodes_lookup(root_node)
all_mitigations = collect_unique_mitigations(root_node, nodes_lookup)

print("\n\n# Mitigations Details")
print("\nHere we include the descriptions for each mitigation where we determined additional details were warranted. There are some mitigations that we believed were sufficiently described by the title, previous similar mitigations or by the contexts where thy have been referenced in the trees -- for these mitigations we did not include a subsection in the following.")
for mitigation in all_mitigations:
	if node_has_description(mitigation):
		print("\n## Mitigation %s" % get_node_title(mitigation).replace('Mitigation: ', ''))
		print("\n%s" % get_description(mitigation))


