var margin = {top: 10, right: 24, bottom: 22, left: 40};
var argv = {height: -1, width: 2700, r: false};
var root;
var svg;
const d3exp = require("d3"); 
var root_node;

function get_raw_description(d) {
    var description = ((d.data.attr || {}).note || {}).text || '';
    if (description === '') {
        description = ((d.data.attr || {}).attachment || {}).content || '';
    }

    return description;
}

function is_freeheight_layout() { return true }

function get_title(d) {
    return d.data.title || '';
}

function is_leaf(d) {
    return typeof d.children === 'undefined';
}

function is_mitigation(d) {
    return is_leaf(d) && /Mitigation: /.test(get_title(d));
}

function hide_children(d) {
    //if (is_leaf(d)){
        d.attr("visibility", "hidden");
}

function is_all(d, predicate) {
    if (typeof d.children === 'undefined') return True;
    if (d.children == null){return true;}

    result = true;
    d.children.forEach(function(d) {
            result = result & predicate(d);
            });

    return result;
}

function toggle(d){
        if(d.children){
                d._children = d.children;
                d.children = null;
        }else{
                d.children = d._children;
                d._children = null;
        }
}

function is_attack_vector(d) {
    if (! is_leaf(d)) {
        return is_all(d, is_mitigation);
    } else {
        return ! is_mitigation(d);
    }
}

function is_reference(d) {
    return ( get_title(d).search("\\(\\*\\)") !== -1  ) || (/\(\d+\..*?\)/.test(get_title(d)));
}

function is_out_of_scope(d) {
    return /out of scope/i.test(get_raw_description(d));
}

function get_node_from_idea(idea){
    return root_node[idea];
}



///-- start D3 code
function do_draw(node_rendering) {
    //Wow, this is embarrassing. Please look away!
    // 'works' only for 10pt sans-serif, here, when stars are properly aligned
    if(node_rendering){
        d3 = d3exp;
    }
    var approxTextWidth = (function() {
            function charW(w, c) {
            if (c == 'W' || c == 'M') w += 15;
            else if (c == 'w' || c == 'm') w += 12;
            else if (c == 'I' || c == 'i' || c == 'l' || c == 't' || c == 'f') w += 4;
            else if (c == 'r') w += 8;
            else if (c == c.toUpperCase()) w += 12;
            else w += 10;
            return w;
            }

            return function(s) {
            return s.split('').reduce(charW, 0) / 2;
            };
            })();

    // TextHeight Configuration
    var text_line_height = 10 * 1.1;
    var node_width_size;
    var node_height_size;
    if (argv.width !== -1 && argv.height == -1) {
        max_depth = 0;
        root_node.each(function(d){
                max_depth = Math.max(max_depth, d.depth);
                });
        available_text_width = Math.floor((argv.width - margin.left - margin.right) / (max_depth+1));

        node_width_size = available_text_width;
        //when not doing a dendrogram, the leaf nodes only get half the width for text
        if (!argv.r) {
            available_text_width = available_text_width / 2.0;
        }

        max_text_height = 0;
        root_node.each(function(d){
                if (argv.r && typeof d.children !== 'undefined') return;

                approx_height = Math.ceil(approxTextWidth(d.data.title) / available_text_width) * text_line_height;
                max_text_height = Math.max(max_text_height, approx_height);
                });
        node_height_size = max_text_height;

        if (argv.r) {
            node_height_size = node_height_size * 1.2;
        }
    }


    width1 = argv.width - margin.left - margin.right;

    if (node_rendering){
        svg = node_rendering.createSVG();
    }else{
    svg = d3.select("svg"), width = +svg.attr("width"),
        height = +svg.attr("height"),
        g = svg.append("g").attr("transform", "translate(" + (width/2 + 40 + "," + (height / 2 + 90) + ")"));
    }
    var tree_maker;
    if (argv.r) {
        //dendrograms
        tree_maker = d3.cluster();
    }
    else {
        tree_maker = d3.tree();
    }

    var tree;
    if (is_freeheight_layout()) {
        tree = tree_maker.nodeSize([node_height_size, node_width_size]); //TODO why's all my stuff rotated 90deg?
    } else {
        var height;
        if (argv.r) {
            leaf_count = 0;
            root_node.each(function(d){
                    if (typeof d.children !== 'undefined') return;

                    leaf_count = leaf_count + 1;
                    });

            height = (node_height_size + text_line_height) * leaf_count + 1 * text_line_height;
        } else {
            height = argv.height - margin.top - margin.bottom;
        }
        tree = tree_maker.size([height, width - node_width_size / 2 - margin.right]);
    }

    var tree_data = tree(root_node).descendants().slice(1);

    // For freeheight layouts, translate to keep all nodes in-view
    if (is_freeheight_layout()) {
        var min_x = Number.MAX_SAFE_INTEGER;
        root_node.each(function(d){
                min_x = Math.min(min_x, d.x);
                });

        root_node.each(function(d){
                d.x = d.x - min_x;
                });
    }

    // calculate the overall height
    max_x = 0;
    root_node.each(function(d){
            max_x = Math.max(max_x, d.x);
            });

    height = max_x + node_height_size;
    total_width = width1 + margin.left + margin.right;
    total_height = height + margin.top + margin.bottom;
    if(node_rendering){
        node_rendering.width = total_width;
    }
    
    // Create the main container
    svg = svg
        .attr("width", total_width)
        .attr("height", total_height)
        .attr("viewBox", "0 0 " + total_width + " " + total_height)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var text_wrap_width = Number.MAX_SAFE_INTEGER;
    root_node.each(function(d){
            if (d.parent === null) return;

            text_wrap_width = Math.min(text_wrap_width, d.y - d.parent.y);
            });
    text_wrap_width = 0.9 * text_wrap_width;

    // In a dendrogram, give the leaf nodes more room -- but do it after sizing to *compensate* for the d3 rendering, not influence it.
    if (argv.r) {
        root_node.each(function(d){
                if (typeof d.children === 'undefined') {
                d.y = d.y - node_width_size / 2;
                }
                });
    }

    // In a dendrogram, bump the next sibling of blocks with looooong text
    if (argv.r) {
        root_node.each(function(d){
                if (typeof d.children !== 'undefined') return;
                if (d.parent === null) return;

                text_line_count = Math.ceil(approxTextWidth(d.data.title) / text_wrap_width);
                text_height = text_line_height * text_line_count;

                d.parent.children.forEach(function(child){
                        if (child.x > d.x && child.x < d.x + text_height) {
                        child.x = child.x + text_line_height;
                        }
                        });
                });
    }

    // a colormap for EVITA attack probability total where 1 is remote and 5 is highly likely
    apt_colormap = function palette(min, max) {
        var d = (max-min)/5;
        return d3.scaleThreshold()
            .range(['#add8e6','#a3eb92','#ffd700','#ffce69','#ffc0cb'])
            .domain([min+1*d,min+2*d,min+3*d,min+4*d,min+5*d]);
    }(1,5);
    var link = svg.selectAll(".link")
        .data(tree_data)
        .enter().append("path")
        .attr("class", "link")
        .style("stroke", function(d) {
                if (typeof d.parent.data.attr !== 'undefined' &&
                        typeof d.parent.data.attr.evita_apt !== 'undefined' &&
                        typeof d.data.attr !== 'undefined' &&
                        typeof d.data.attr.evita_apt !== 'undefined') {
                return apt_colormap(d.data.attr.evita_apt);
                }
                })
    .attr("d", function(d) {
            elbow_point = (d.parent.y + 6*(d.y - d.parent.y) / 10);

            if (argv.r) {
            elbow_point = d.parent.y;

            if (d.parent.parent === null) {
            var min_y = d.y;
            d.parent.children.forEach(function(entry){
                    min_y = Math.min(min_y, entry.y);
                    });
            elbow_point = (d.parent.y + (min_y - d.parent.y) / 2);
            }
            }

            var this_childs_index = 0.0;
            var siblings_count = 0.0;
            if (d.parent !== null) {
            var count = 0;
            siblings_count = d.parent.children.length;
            d.parent.children.forEach(function(entry){
                    count = count + 1;
                    if (entry == d && d.parent.children.length > 1) {
                    this_childs_index = (count - siblings_count / 2.0 - 0.5) * 2.0;
                    }
                    });
            }
            return "M" + d.parent.y + "," + d.parent.x
                + "l" + Math.abs(this_childs_index) + "," + this_childs_index
                + "H" + elbow_point
                + "V" + d.x + "H" + d.y;
    });


    function d3TextWrap(text, width) {
        var arrLineCreatedCount = [];
        text.each(function() {
                var text = d3.select(this),
                words = text.text().split(/[ \f\n\r\t\v]+/).reverse(), //Don't cut non-breaking space (\xA0), as well as the Unicode characters \u00A0 \u2028 \u2029)
                word,
                line = [],
                lineNumber = 0,
                lineHeight = 1.05, //Ems
                x = text.attr("x"),
                y = text.attr("y"),
                createdLineCount = 1; //Total line created count
                var textAlign = text.style('text-anchor') || 'left';
                var alignmentBase = text.style('alignment-baseline') || 'baseline';
                var adjusted_width = width;
                var node = text.datum();
                if (node.parent === null) {
                    adjusted_width = width/2 + margin.left;
                }
                else if (is_attack_vector(node) || is_mitigation(node)) {
                    if (! argv.r) {
                        adjusted_width = 5/8 * width;
                    }
                }

                dy = 0;
                x = 0;
                if (textAlign === 'start') {
                    x = 8;
                }
                if (text.datum().parent === null) {
                    x = x - margin.left;
                }

                y = 3;
                if (alignmentBase === 'hanging') {
                    y = 12;
                } else if (alignmentBase === 'ideographic') {
                    y = -6;
                }

                var tspan = text.text(null).append("tspan").attr("x", x).attr("y", y).attr("dy", dy + "em");

                while (word = words.pop()) {
                    line.push(word);
                    tspan.text(line.join(" "));
                    if (approxTextWidth(line.join(" ")) > adjusted_width && line.length > 1) {
                        line.pop();
                        tspan.text(line.join(" "));
                        line = [word];
                        tspan = text.append("tspan").attr("x", x).attr("y", y).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word); //TODO: don't use dy -- it is making glitches in jsdom; instead increment by 1.1* font size in px (assume 10 for now)
                        ++createdLineCount;
                    }
                }

                arrLineCreatedCount.push(createdLineCount); //Store the line count in the array
        });
        return arrLineCreatedCount;
    }


    var node = svg.selectAll(".node")
        .data(root_node.descendants())
        .enter().append("g")
        .attr("class", function(d) {
                if (is_attack_vector(d)) {
                if (is_reference(d)) {
                return "node node--vector_ref";
                } else if (is_out_of_scope(d)) {
                return "node node--vector_oos";
                } else {
                return "node node--vector";
                }
                } else if (is_mitigation(d)) {
                if (is_reference(d)) {
                return "node node--mitigation_ref";
                } else {
                return "node node--mitigation";
                }
                } else {
                return "node node--internal";
                }
                return "node node--internal"; 
                })
    .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })
    .on("click", function(d,i){
            if(!is_mitigation(d)){
                toggle(d);
                svg.selectAll("*").remove();
            } else{
                d.attr("visibility", "hidden");
            }
            do_draw(node_rendering);
        })

        node.append("circle")
        .filter(function (d) { return ! is_mitigation(d); })
        .style("stroke", function(d) {
                if (typeof d.data.attr !== 'undefined')
                return apt_colormap(d.data.attr.evita_apt);
                })
    .attr("r", 2.5);

    node.append("rect")
        .filter(function (d) { return is_mitigation(d); })
        .style("stroke", function(d) {
                if (typeof d.data.attr !== 'undefined')
                return apt_colormap(d.data.attr.evita_apt);
                })
    .attr("width", 5.0)
        .attr("heigth", 5.0);

    node.append("text")
        .attr("dy", 3)
        .attr("x", function(d) { return d.children ? -8 : 8; })
        .style("text-anchor", function(d) {
                if (d.parent === null) {
                return "start";
                }
                return (is_attack_vector(d) || is_mitigation(d)) ? "start" : "middle";
                })
    .style("alignment-baseline", function(d) {
            if (d.data.title === "AND") {
            return "middle";
            }
            if (d.parent === null) {
            return "ideographic";
            }
            return (is_attack_vector(d) || is_mitigation(d)) ? "baseline" : "hanging";
            })
    .style("fill", function(d){
        if (d._children == null || d._children == undefined){
            return "normal";
        }else{
            return "purple";
        }
    })
    .text(function(d) { return d.data.title; })
        .call(d3TextWrap, text_wrap_width, 0, 0);


}

function mup_init(filedata, svg_exported_object){
        //console.log(__dirname);
        //if (data != null){
            //console.log(filedata);
        if (svg_exported_object){
            const d3 = require("d3");
            root_node = d3.hierarchy(filedata, function(d) {
            if (typeof d.ideas === "undefined"){ return null; }
            if (typeof d.attr !== "undefined" && typeof d.attr.collapsed !== "undefined" && d.attr.collapsed === true) { return null; }
            //sort(...) orders the ideas the same as the children are ordered in mindmup
            return Object.keys(d.ideas).sort(function(a,b) { return a - b; }).map(key => d.ideas[key]);
            });

        root = filedata;
        do_draw(svg_exported_object);
        }else{
        d3.json(filedata, function(data){
        //data = JSON.parse("The Bottom Line.mup");
        root_node = d3.hierarchy(data, function(d) {
            if (typeof d.ideas === "undefined"){ return null; }
            if (typeof d.attr !== "undefined" && typeof d.attr.collapsed !== "undefined" && d.attr.collapsed === true) { return null; }
            //sort(...) orders the ideas the same as the children are ordered in mindmup
            return Object.keys(d.ideas).sort(function(a,b) { return a - b; }).map(key => d.ideas[key]);
            });

        root = data;
        do_draw(svg_exported_object);
    });
    }
}

function update(source){
        var nodes = root_node.nodes(root).reverse(); 
        var node = svg.selectAll("g.node").data(nodes,function(d) { return d.id || (d.id = ++i);});
        var link = svg.selectAll("path.link").data(root_node.links(nodes),function(d) {return d.target.id;});
}
module.exports.mup_init = mup_init;