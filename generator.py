#!/usr/bin/env python
"""

Neural SPARQL Machines - Generator module

'SPARQL as a Foreign Language' by Tommaso Soru and Edgard Marx et al., SEMANTiCS 2017
https://w3id.org/neural-sparql-machines/soru-marx-semantics2017.html
https://arxiv.org/abs/1708.07624

Version 0.0.4

"""
import sys
import json
import urllib2, urllib, httplib, json
import random
import re
import os

reload(sys)
sys.setdefaultencoding("utf-8")

ENDPOINT = "http://live.dbpedia.org/sparql"
GRAPH = "http://dbpedia.org"

TARGET_CLASS = "dbo:Monument"

EXAMPLES_PER_TEMPLATE = 1
BASE_DIR = "data/movies_300_nsp/"
ANNOT_DIR = 'data/movies_annots/'

# ================================================================

def sparql_query(query):
    param = dict()
    param["default-graph-uri"] = GRAPH
    param["query"] = query
    param["format"] = "JSON"
    param["CXML_redir_for_subjs"] = "121"
    param["CXML_redir_for_hrefs"] = ""
    param["timeout"] = "600000" # ten minutes - works with Virtuoso endpoints
    param["debug"] = "on"
    try:
        resp = urllib2.urlopen(ENDPOINT + "?" + urllib.urlencode(param))
        j = resp.read()
        resp.close()
    except (urllib2.HTTPError, httplib.BadStatusLine):
        print "*** Query error. Empty result set. ***"
        j = '{ "results": { "bindings": [] } }'
    sys.stdout.flush()
    return json.loads(j)

def extract(data):
    res = list()
    for result in data:
        res.append(result)
    # print res
    
    if len(res) == 0:
        return None
    
    indx = set()
    while True:
        indx.add(int(random.random() * len(res)))
        print indx
        if len(indx) == EXAMPLES_PER_TEMPLATE or len(indx) == len(res):
            break
    
    xy = list()
    for i in indx:
        result = res[i]
        x = result["x"]["value"]
        lx = result["lx"]["value"]
        print "x = {} -> {}".format(x, lx)
        try:
            y = result["y"]["value"]
            ly = result["ly"]["value"]
            print "y = {} -> {}".format(y, ly)
        except KeyError:
            y = None
            ly = None
        xy.append((x,lx,y,ly))
        
    return xy
    
def strip_brackets(s):
    # strip off brackets
    s = re.sub(r'\([^)]*\)', '', s)
    # strip off everything after comma
    if "," in s:
        s = s[:s.index(",")]
    # strip off spaces and make lowercase
    return s.strip().lower()
    
def replacements(s):
    repl = []
    with open('sparql.grammar') as f:
        for line in f:
            line = line[:-1].split('\t')
            spaces = list()
            for i in range(4):
                if line[i+2] == '1':
                    spaces.append(' ')
                else:
                    spaces.append('')
            repl.append((spaces[0] + line[0] + spaces[1], spaces[2] + line[1] + spaces[3]))
    for r in repl:
        s = s.replace(r[0], r[1])
    return s

def recheck(s):
    s2 = s.split(' ')
    old = None
    for i in range(len(s2)):
        # print i, s2
        if i == len(s2):
            break
        token = s2[i]
        # fix problem with missing trailing ')'
        if old is not None:
            if old.startswith("dbr_") or old.startswith("dbo_"):
                if token == "par_close":
                    s2[i-1] += ')'
                    s2 = s2[:i] + s2[i+1:]
                    i -= 1
        old = token        
    s = " ".join(s2)
    # order by desc par_open X par_close -> obd X
    print "BEFORE:", s
    s = re.sub(r'order by desc par_open ([^\s]+) par_close', 'obd \\1', s)
    # order by asc par_open X par_close -> obd X (uncommon, but possible)
    s = re.sub(r'order by asc par_open ([^\s]+) par_close', 'oba \\1', s)
    # order by X -> oba X
    s = re.sub(r'order by ([^\s]+)', 'oba \\1', s)
    for key, value in { 'days': 86400, 'hours': 3600, 'minutes': 60, 'seconds': 1 }.items():
        # e.g., filter par_open X F Y math_mult 3600 par_close -> filter_hours X F Y
        s = re.sub(r'filter par_open ([^\s]+) ([^\s]+) ([^\s]+) math_mult {} par_close'.format(value), 'filter_{} \\1 \\2 \\3'.format(key), s)
    print "AFTER:", s
    return s
    
# ================================================================

annot = list()
for i in range(3):
    fname = ANNOT_DIR + 'annotations_{}.tsv'.format(i)
    if os.path.isfile(fname):
        with open(fname) as f:
            for line in f:
                annot.append(tuple(line[:-1].split('\t')))

cache = dict()
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)
with open(BASE_DIR + 'data_300.en', 'w') as f1:
    with open(BASE_DIR + 'data_300.sparql', 'w') as f2:
        for a in annot:
            print a
            if a[2] in cache:
                results = cache[a[2]]
            else:
                q = a[2].replace(" C ", " {} ".format(TARGET_CLASS)).replace(" where { ", " (str(?labx) as ?lx) where { ?x rdfs:label ?labx . FILTER(lang(?labx) = 'en') . ")
                if "?y" in q:
                    q = q.replace(" where { ", " (str(?laby) as ?ly) where { ?y rdfs:label ?laby . FILTER(lang(?laby) = 'en') . ")
                print q
                results = sparql_query(q)
                cache[a[2]] = results
            print "\n====> " + a[0] + " <====="
            print "ans length = {}".format(len(str(results)))
    
            if a[2] == "/": # no generator query available
                xy_array = [("", "", "", "")]
            else:
                xy_array = extract(results["results"]["bindings"])
            if xy_array is None:
                print "\nNO DATA FOR '{}'".format(a[0])
                continue
            
            for xy in xy_array:
                inp = a[0].replace("<A>", strip_brackets(xy[1]))
                outp = a[1].replace("<A>", xy[0])
                if "<B>" in inp:
                    if xy[3] is not None:
                        inp = inp.replace("<B>", strip_brackets(xy[3]))
                    else:
                        print "ERROR. Templates not added: xy[3] is none."
                        continue
                if "<B>" in outp:
                    if xy[2] is not None:
                        outp = outp.replace("<B>", xy[2])
                    else:
                        print "ERROR. Templates not added: xy[2] is none."
                        continue
                outp = replacements(outp)
                outp = recheck(outp)
    
                print "\n{}\n{}\n{}".format(xy, inp, outp)
                f1.write("{}\n".format(inp))
                f2.write("{}\n".format(outp))
