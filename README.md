# ```mindmup-as-attack-trees```

Python scripts for using mindmup `.mup` JSON as a medium for developing attack trees.

# In General:

1. Create an attack tree with [mindmup](https://app.mindmup.com/map/new/) -- legacy version 1 also supported.

1. Save the `.mup` locally

1. Use these scripts to do the following steps (can be done indivdiually or in a batch depending on your workflow).

|    | Step Description                                                                                                       | Script in `scripts/` |
|---:|:-----------------------------------------------------------------------------------------------------------------------|:------:|
|   0| normalize the `.mup` JSON -- useful before comitting to SCM to reduce diff noise                                       |```normalize-json```|
|   1| check the `.mup` for problems (e.g. duplicate nodes, missing references, missing EVITA:: tags) and strips hidden sections                         |```checks.py``` |
|   2| number the nodes in the `.mup`, resolving references to nodes in the tree (and undo this)                              |```add-numbered-ids.py``` (```remove-numbered-ids.py```) |
|   3| resolve any 'in-text' references to nodes                                                                              |```resolve-mup.py``` |
|   4| propagate and calculate the required attack potentials and risks based on the model in the `.mup` file (and undo this) |```add-evita.py``` (```remove-evita.py```) |
|   5| generate a report from the `.mup` -- including renderings of the subtrees as images in-line                            |```generate-descriptions-md-template``` |
|   6| generate a risk analysis section for the report from the `.mup`                                                        |```generate-evita-chart.py``` |

1. Publish the report as markdown+images or convert to format of your choice (with e.g. `pandoc`)

# In Detail:

1. Collaborate on (this was alot better before mindmup 2.0), or otherwise create an attack tree in [mindmup](https://app.mindmup.com/map/new/).
    * This `.mup` file will serve as the container for the attack trees from objectives through attack vectors to mitigations -- including also descriptive text and weightings for severities and required attack potentials.
    * There are some special strings and properties that will be recognized by the processing later:
        * ```AND``` for an and-ing operation on subtrees
        * ```(*)``` for references to other nodes defined elsewhere in the tree
        * ```...``` for nodes unspecified
        * ```.hidden`` for hiding nodes in the .mup that will not be rendered in the report
        * ```Mitigation: <anything>``` for capturing mitigations to attacks both on attack vectors and mid-tree

    * There are some special 'tags' that should be inserted in the descriptions of the nodes
        * ```OBJECTIVE::``` for classifying a node as an attacker objective, where both attacker motivation and impact on stakeholders is clear also
        * ```RISK_HERE::``` for specifying a point in the tree where risk should be calculated, if in doubt place these on `OBJECTIVE::` nodes
        * ```OUT_OF_SCOPE::``` for marking a node out-of-scope for this analysis. This node will still need estimated Required Attack Potentials but does not need to have its subtree expanded in detail or any mitigations captured
        * ```EVITA:: |S|S|S|S|R|R|R|R|R``` for ascribing estimates of *severity* (`S` fields) and estimates of *Required Attack Potential* (RAP) (`R` fields). These are required on `OBJECTIVE::` nodes and also for attack vectors. Severities are ascribed to `OBJECTIVE::` nodes, whereas RAPs are ascribed to attack vectors.
        * ```SUBTREE::``` for breaking-up large attack trees into smaller 'snapshots'/'subtrees' when rendered in the report

    * Finally, any free-form text can be put into the node descriptions as markdown (saved as HTML-wrapped markdown). You should include descriptions of any attack vector nodes as well as some justification text of the RAPs ascribed. Similarly for objective nodes, descriptions should be written that explain attacker motivations and justify the severities ascribed.

1. download the mindmup ```.mup``` file

    e.g. see ```examples/steps/0_Compromise (P)RNG Somehow.mup```

1. normalize the JSON with ```normalize-json```. This is useful if you are going to commit the mindmup to a SCM as it will minimize line-diffs in the future.

    e.g. ```normalize-json < examples/steps/0_Compromise\ \(P\)RNG\ Somehow.mup > examples/steps/1_Compromise\ \(P\)RNG\ Somehow.mup```

1. add numbering to the tree with ```add-numbered-ids.py```
    * you can later re-number the nodes by running ```remove-numbered-ids.py``` then ```add-numbered-ids.py``` again.

    e.g. ```add-numbered-ids.py < examples/steps/1_Compromise\ \(P\)RNG\ Somehow.mup examples/steps/2_Compromise\ \(P\)RNG\ Somehow.mup```

1. add calculations of all Required Attack Potentials troughout the tree and estimates of risk as the `RISK_HERE::` with ```add-evita.py```.
    * you can later re-calculate these by running ```remove-evita.py``` then ```add-evita.py``` again.

    e.g. ```add-evita.py < examples/steps/0_Compromise\ \(P\)RNG\ Somehow.mup > examples/steps/1_Compromise\ \(P\)RNG\ Somehow.mup```

1. generate a template report for the now-numbered tree using ```generate-descriptions-md-template```. This will create a markdown template and some subtrees snapshot ```.mup``` files. The template includes inline ```.png``` images that need to be rendered from those ```.mup``` files.

    e.g. ```mkdir examples/steps/3_Report && cd examples/steps/3_Report && ../../../generate-descriptions-md-template < ../2_Compromise\ \(P\)RNG\ Somehow.mup > Report.md```

1. for each of the subtree snapshot ```.mup``` files: render a .png file using ```rendermup```

1. add a risk analysis section to the report with ```generate-evita-chart.py```

1. iteratively edit the template, including descriptions, impacts, severities etc. to achieve a draft report

1. publish the markdown+images.

# Calculation of Combined Attack Probability and Risk

By adding tags to the mindmup text you can structure the attack tree to include attacker objectives with associated severities and attack vectors with associated required attack potentials. Then the scripts will calculate and propagate the required attack potentials up the tree and marry them with the severities to estimate risks. This calculation is performed according to the method detailed in [*Security requirements for automotive on-board networks based on dark-side scenarios*](https://rieke.link/EVITAD2.3v1.1.pdf)
