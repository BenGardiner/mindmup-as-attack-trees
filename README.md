# ```mindmup-as-attack-trees```
Python scripts for using mindmup JSON as a medium for developing attack trees

# Workflow

In general:

1. Create an attack tree with [mindmup](mindmup.com)

1. Download it, add numbers to it and generate a report template from it.

1. Render the snapshot subtrees for the report through mindmup export as PNG

1. Publish the markdown+images

In detail:

1. collaborate on (this was alot better before mindmup 2.0), or otherwise create an attack tree in [mindmup](mindmup.com).
	* It is best if this tree is stable, making large changes to it will make it hard to update the derived documents generated in later steps.
	* There are some special strings and properties that will be recognized by the processing later:
		* ```AND``` for an and-ing operation on subtrees
		* ```(*)``` for subtres-by-reference to nodes already defined in the tree
		* ```...``` for nodes unspecified

1. download the mindmup ```.mup``` file

	e.g. see ```examples/steps/0_Compromise (P)RNG Somehow.mup```

1. normalize the JSON with ```scripts/normalize-json```. This is useful if you are going to commit the mindmup file as it will minimize line-diffs in the future.

	e.g. ```./scripts/normalize-json < examples/steps/0_Compromise\ \(P\)RNG\ Somehow.mup > examples/steps/1_Compromise\ \(P\)RNG\ Somehow.mup```

1. add numbering to the tree with ```scripts/add-numbered-ids.py```
	* you can later re-number the nodes by running ```scripts/remove-numbered-ids.py``` then ```scripts/add-numbered-ids.py``` again.

	e.g. ```./scripts/add-numbered-ids.py < examples/steps/1_Compromise\ \(P\)RNG\ Somehow.mup | ./scripts/normalize-json > examples/steps/2_Compromise\ \(P\)RNG\ Somehow.mup```

1. generate a template report for the now-numbered tree using ```scripts/generate-descriptions-template.md [cut levels ...]```. This will create a markdown template and some subtrees snapshot ```.mup``` files. The template includes inline ```.png``` images that need to be rendered from those ```.mup``` files.

	e.g. ```mkdir examples/steps/3_Report && cd examples/steps/3_Report && ../../../scripts/generate-descriptions-template.md 2. < ../2_Compromise\ \(P\)RNG\ Somehow.mup > Report.md```

1. for each of the subtree snapshot ```.mup``` files: render a .png file at [mindmup](mindmup.com) and save them (e.g. ```A.mup``` to ```A.png```).

1. iterativley edit the template, including descriptions, impacts, severities etc. to achieve a draft report

1. publish the markdown+images.

