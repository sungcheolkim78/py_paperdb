""" bibdb.py """

import os
import glob
import requests
import pandas as pd
import numpy as np

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

from arxiv2bib import arxiv2bib

from py_readpaper import find_author1

def read_bib(filename):
    """ read bibtex file and return bibtexparser object """

    if not os.path.exists(filename):
        print("... no bib file: {}".format(filename))
        os.exit(0)

    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    parser.homogenise_fields = False

    with open(filename) as f:
        bibtex_str = f.read()

    bib_database = bibtexparser.loads(bibtex_str, parser)
    return bib_database


def to_bib(pd_db, filename, fromDict=False):
    """ save panda bib records into file """

    if fromDict:
        items = pd_db
    else:
        items = pd_db.astype(str).to_dict("records")

    db = BibDatabase()

    db.entries = items

    writer = BibTexWriter()
    with open(filename, 'w') as bibfile:
        bibfile.write(writer.write(db))

    print('... save to {}'.format(filename))


def read_paperdb(filename, update=False):
    """ read bib file or csv file """

    fname_csv = ''.join(filename.split('.')[:-1]) + '.csv'
    if (not update) and os.path.exists(fname_csv):
        print('... read from {}'.format(fname_csv))
        p = pd.read_csv(fname_csv, index_col=0)
    else:
        bib = read_bib(filename)
        p = pd.DataFrame.from_dict(bib.entries)
        p = clean_db(p)
        p.to_csv(fname_csv)
        print('... save to {}'.format(fname_csv))

    return clean_db(p)


def read_bibfiles(globpattern="*.bib", update=False):
    """ read bib files with glob pattern """

    flist = glob.glob(globpattern)
    if len(flist) == 0:
        print("... no bib files")
        return

    res = pd.DataFrame()

    for f in flist:
        p = read_paperdb(f, update=update)
        res = pd.concat([res, p], ignore_index=True, sort=False)

    # sort by year and author1
    res.sort_values(by=['year', 'author1'], inplace=True)
    res.index = range(len(res))

    res.fillna('', inplace=True)

    return res


def clean_db(p):
    """ read bib file and convert it to panda db and save to csv """

    # check NA
    if 'read' in p.columns:
        p['read'] = p['read'].fillna('False')
    else:
        p['read'] = False
    p = p.fillna('')

    # check uri and obtain doi
    if "uri" in p.columns:
        if 'doi' not in p.columns:
            p['doi'] = p['uri'].str.slice(31, -1)    # 31 can be different depending on papers
        p.drop(columns=['uri'], inplace=True)

    p['doi'] = p['doi'].str.replace("https://doi.org/","")

    # check urls
    if 'url' not in p.columns:
        p['url'] = ''
    urls = p['url']
    if "bdsk-url-1" in p.columns:
        burl1s = p['bdsk-url-1']
        burl2s = p['bdsk-url-2']
        for i in range(len(urls)):
            urlset = set([urls[i], burl1s[i], burl2s[i]])
            urlset = urlset.difference(set(['']))
            if len(urlset) == 0:
                urls[i] = ''
            else:
                urls[i] = str(urlset.pop())
        p['url'] = urls
        p.drop(columns=['bdsk-url-1', 'bdsk-url-2'], inplace=True)

    if "bdsk-file-1" in p.columns:
        p.drop(columns=['bdsk-file-1'], inplace=True)

    if "file" in p.columns:
        p.drop(columns=['file'], inplace=True)

    # add first author column
    if "author" in p.columns:
        p["author1"] = [ find_author1(x) for x in p['author'].values ]
    else:
        p["author"] = ''
        p["author1"] = ''

    if "pmid" in p.columns:
        p["pmid"] = p["pmid"].astype(str)
    else:
        p['pmid'] = ''

    if "pmcid" in p.columns:
        p["pmcid"] = p["pmid"].astype(str)
    else:
        p['pmcid'] = ''

    # sort
    p.sort_values(by=['year', 'author'], inplace=True)
    p.index = range(len(p))

    return p


def find_bib_dict(pd_db, bib_dict, index=False, threshold=0.5, debug=False):
    """ find duplicated items """

    pd_db["score"] = np.array([ compare_bib_dict(bib_dict, pd_db.loc[x]) for x in pd_db.index ])

    res = pd_db.loc[pd_db["score"] > threshold]
    #res = res.append(bib_dict, ignore_index=True)

    if index:
        if debug: print(res)
        return res.index, pd_db.loc[pd_db["score"] > threshold, "score"].values
    else:
        return res


def compare_bib_dict(item1, item2):
    """ compare bibtex item1 and item 2 in dictionary form """

    # unique id check
    col_list = ["doi", "pmid", "pmcid", "title", "local-url"]

    for c in col_list:
        if (item1.get(c, "1") != '') and (item1.get(c, "1") == item2.get(c, "2")):
            return 1.0

    score = 0.0

    def _get_score(item1, item2, colname, s):
        if item1.get(colname, "1") == '': return 0.0
        if item1.get(colname, "2") == '': return 0.0
        if item1.get(colname, "1") == item2.get(colname, "2"): return s
        return 0.0

    score = score + _get_score(item1, item2, "year", 0.2)
    score = score + _get_score(item1, item2, "author", 0.2)
    score = score + _get_score(item1, item2, "author1", 0.1)
    score = score + _get_score(item1, item2, "journal", 0.2)
    score = score + _get_score(item1, item2, "volume", 0.1)

    return score


def merge_items(pd_db, idx1, idx2, debug=False):
    """ merge two items in pd db """

    if idx1 == idx2: return (False, pd_db)

    score = compare_bib_dict(pd_db.loc[idx1], pd_db.loc[idx2])

    if score < 0.8:
        print('... two entries ({}, {}) are different: {}'.format(idx1, idx2, score))
        if debug: print(pd_db.loc[[idx1, idx2]])
        return (False, pd_db)

    for col in pd_db.columns:
        if pd_db.loc[idx1, col] is '':
            pd_db.loc[idx1, col] = pd_db.loc[idx2, col]

    if debug:
        print('... ({}, {}) are merged: {}'.format(idx1, idx2, score))
        print(pd_db.loc[[idx1, idx2]])

    return (True, pd_db.drop([idx2]))
