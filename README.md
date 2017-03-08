# ```mindmup-as-attack-trees```
Python scripts for using mindmup JSON as a medium for developing attack trees

# Workflow

In general:

1. Create an attack tree with [mindmup](https://app.mindmup.com/map/new/)

1. Download it, add numbers to it and generate a report template from it.

1. Render the snapshot subtrees for the report through mindmup export as PNG

1. Publish the markdown+images

In detail:

NB: the commands below haven't been updated to reflect some of the more recent changes to these scripts

1. collaborate on (this was alot better before mindmup 2.0), or otherwise create an attack tree in [mindmup](https://app.mindmup.com/map/new/).
	* It is best if this tree is stable, making large changes to it will make it hard to update the derived documents generated in later steps.
	* There are some special strings and properties that will be recognized by the processing later:
		* ```AND``` for an and-ing operation on subtrees
		* ```(*)``` for subtrees-by-reference to nodes already defined in the tree
		* ```...``` for nodes unspecified

1. download the mindmup ```.mup``` file

	e.g. see ```examples/steps/0_Compromise (P)RNG Somehow.mup```

1. normalize the JSON with ```scripts/normalize-json```. This is useful if you are going to commit the mindmup file as it will minimize line-diffs in the future.

	e.g. ```./scripts/normalize-json < examples/steps/0_Compromise\ \(P\)RNG\ Somehow.mup > examples/steps/1_Compromise\ \(P\)RNG\ Somehow.mup```

1. add numbering to the tree with ```scripts/add-numbered-ids.py```
	* you can later re-number the nodes by running ```scripts/remove-numbered-ids.py``` then ```scripts/add-numbered-ids.py``` again.

	e.g. ```./scripts/add-numbered-ids.py < examples/steps/1_Compromise\ \(P\)RNG\ Somehow.mup | ./scripts/normalize-json > examples/steps/2_Compromise\ \(P\)RNG\ Somehow.mup```

1. generate a template report for the now-numbered tree using ```scripts/generate-descriptions-md-template [cut levels ...]```. This will create a markdown template and some subtrees snapshot ```.mup``` files. The template includes inline ```.png``` images that need to be rendered from those ```.mup``` files.

	e.g. ```mkdir examples/steps/3_Report && cd examples/steps/3_Report && ../../../scripts/generate-descriptions-md-template 2.0 2.1 < ../2_Compromise\ \(P\)RNG\ Somehow.mup > Report.md```

1. for each of the subtree snapshot ```.mup``` files: render a .png file at [mindmup](https://app.mindmup.com/map/new/) and save them (e.g. ```A.mup``` to ```A.png```).

1. iteratively edit the template, including descriptions, impacts, severities etc. to achieve a draft report

1. publish the markdown+images.

# Calculation of Combined Attack Probability and Risk

By adding tags to the mindmup text you can structure the attack tree to include attacker objectives with associated severities and attack vectors with associated required attack potentials. Then the scripts will calculate and propagate the required attack potentials up the tree and marry them with the severities to estimate risks. This calculation is performed according to the method detailed in [*Security requirements for automotive on-board networks based on dark-side scenarios*](https://rieke.link/EVITAD2.3v1.1.pdf)
