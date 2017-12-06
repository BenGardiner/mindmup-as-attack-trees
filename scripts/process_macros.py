#!/usr/bin/env python
from mindmup_as_attack_trees import *

import sys,json,getopt
import re
from collections import OrderedDict

macros_lookup={}

def process_macro(elem):
    elems = elem.split("=")
    macros_lookup[elems[0]]=elems[1]

def get_key_name(macro):
    key=''
    if macro.startswith('__M__'):
        key = macro[5:]
    return key

def select_child(node):
    node_title = get_node_title(node)

    #node title must start with 'XOR'
    if not node_title.startswith('XOR'):
        return

    macro=re.findall(r'__M__[A-Z_]+', node_title)[0]

    key_name=get_key_name(macro)
    key_value=int(macros_lookup[key_name])

    selected_child=get_node_children(node)[key_value]

    node.clear()
    node.update(selected_child)

    return

display_set = dict()
def process_pass(node):
    node_title = get_node_title(node)
    node_description = get_raw_description(node)
    if node_title.find("__M__") >= 0 or node_description.find("__M__") >= 0:
        if display_list:
            for match in re.findall(r'__M__[A-Z_]+', node_title + ' ' + node_description):
                if display_set.get(match) is None:
                    print match
                    display_set.update({match: True})
        else:
            if node_title.startswith('XOR'):
                return

            for key_name in macros_lookup.keys():
                node_title = node_title.replace('__M__' + key_name, macros_lookup[key_name])
                set_node_title(node, node_title)
                node_description = node_description.replace('__M__' + key_name,macros_lookup[key_name])
                update_raw_description(node, node_description)

#parse cmd line and populate all pairs to dictionary

fd_in = 0
fd_out = 0
display_list = None

try:
    opts, args = getopt.getopt(sys.argv[1:],"hli:o:D:",["list","ifile=","ofile="])
except getopt.GetoptError:
    print 'process_macros.py -DMACRO=VALUE -i <input file>  -o <output file> '
    print '                  -l --list              list macros'
    print '                  -i --ifile <file name> input file'
    print '                  -o --ofile <file name> output file'
    print '                  -DMACRO=VALUE          macro definition'  
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print 'process_macros.py -DMACRO=VALUE -i <input file>  -o <output file> '
        print '                  -l --list              list macros'
        print '                  -i --ifile <file name> input file'
        print '                  -o --ofile <file name> output file'
        print '                  -DMACRO=VALUE          macro definition' 
        sys.exit()
    elif opt in ("-l", "--list"):
        display_list = True
    elif opt in ("-i", "--ifile"):
        fd_in=open(arg, 'r')   
    elif opt in ("-o", "--ofile"):
        fd_out=open(arg, 'w')
    elif opt in ("-D"):
        process_macro(arg)

if fd_in == 0:
    fd_in=sys.stdin
if fd_out == 0:
    fd_out=sys.stdout

data = json.load(fd_in)

if 'id' in data and data['id'] == 'root':
    #version 2 mindmup
        root_node = data['ideas']['1']
else:
    root_node = data

if display_list:
    apply_each_node(root_node, process_pass)
    sys.exit()

apply_each_node(root_node, process_pass)
apply_each_node(root_node, select_child)

str = json.dumps(data, indent=2, sort_keys=True)
fd_out.write(str)
fd_out.close()

