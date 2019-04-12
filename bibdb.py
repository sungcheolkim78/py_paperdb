""" bibdb.py """

import os
import requests
import pandas as pd

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

from arxiv2bib import arxiv2bib

from py_readpaper import find_author1

def read_bib(filename):
    """ read bibtex file and return bibtexparser object """

    if not os.path.exists(filename):
        print("... no bib file: {}".foramt(filename))
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

    return clean_db(p)


def clean_db(p):
    """ read bib file and convert it to panda db and save to csv """

    # check NA
    p['read'] = p['read'].fillna('False')
    p = p.fillna('')

    # check uri and obtain doi
    if "uri" in p.columns:
        p['doi'] = p['uri'].str.slice(31, -1)    # 31 can be different depending on papers
        p.drop(columns=['uri'], inplace=True)

    # check urls
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

    # add first author column
    p["author1"] = [ find_author1(x) for x in p['author'].values ]
    p["pmid"] = p["pmid"].astype(str)
    p["pmcid"] = p["pmid"].astype(str)

    # sort
    p.sort_values(by=['year', 'author'], inplace=True)
    p.index = range(len(p))

    return p


def find_duplicate(pd_db):
    """ find duplicated items """
    return 0

