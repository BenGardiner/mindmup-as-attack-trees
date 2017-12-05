#!/usr/bin/env node

const fs = require('fs');
const D3Node = require('d3-node');
const d3 = require('d3');
const path = require("path");
const yargs = require('yargs');
const mup = require('./mupcommon.js');
var margin = {top: 10, right: 24, bottom: 22, left: 40};
const argv = yargs
    .usage(`rendermup input.mup`)
    .demand(1)
    .option("w", {
        alias: "width",
        type: "number",
        describe: "The output file width, in pixels",
        default: "1260"
    })
    .option("h", {
        alias: "height",
        type: "number",
        describe: "The output file height, in pixels",
        default: "-1"
    })
    .option("r", {
        alias: "right-justified",
        type: "boolean",
        describe: "render the tree with all leaves at the right (i.e. cluster/dendrogram layout)",
        default: "false"
    })
    .help(false)
    .argv;

const styles = fs.readFileSync("./mupstyle.css");
const input = fs.readFileSync(argv._[0], 'utf8');
inputHtmlFiledata = fs.readFileSync("stubbedhtml.html");
const outputHtmlFilename = path.basename(argv._[0], ".mup") + ".html";
const outputSvgFilename = path.basename(argv._[0], ".mup") + ".svg";
const outputPngFilename = path.basename(argv._[0], ".mup") + ".png";

mindmup_json = JSON.parse(input);
//width = 2100;
markup = '<div id="container"><div id="chart"></div></div>';
//markup = '<meta http-equiv="refresh" content="3">' + markup;
var options = {selector:'#chart', svgStyles:styles, container:markup, d3Module:d3};

var d3n = new D3Node(options);
//console.log("__dirname: "+__dirname);
//console.log(buffer.toString());
mup.mup_init(mindmup_json, d3n);

/// -- end D3 code

// create output files
const svg2png = require('svg2png');
console.log(inputHtmlFiledata.toString());
inputHtmlFiledata = inputHtmlFiledata.toString().replace("%%filename%%",path.basename(argv._[0]));
console.log(inputHtmlFiledata.toString());
fs.writeFile(outputHtmlFilename, inputHtmlFiledata, function () {
  console.log('>> Done. Open '+outputHtmlFilename+'" in a web browser');
});

var svg_string = d3n.svgString();
fs.writeFile(outputSvgFilename, svg_string, function () {
  console.log('>> Exported: "'+outputSvgFilename+'"');
});

var svgBuffer = new Buffer(svg_string, 'utf-8');
//console.log(d3n.width);
//console.log(svgBuffer.toString());
svg2png(svgBuffer,  {width: d3n.width*4})
  .then(buffer => fs.writeFile(outputPngFilename, buffer))
  .catch(e => console.error('ERR:', e))
  .then(err => console.log('>> Exported: "'+outputPngFilename+'"'));