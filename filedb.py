"""
filedb.py

update pdf file metadata
"""

import glob
import random
import pandas as pd
import numpy as np
from tqdm import tqdm, tqdm_notebook

from py_readpaper import Paper


# file db structure
# local-url, year, author1, journal, title, doi, keywords, abstract, extra, sync

def read_dir(dirname='.', debug=False):
    """ from file list and filenames build panda db """

    flist = sorted(glob.glob(dirname + '/*.pdf'))
    if len(flist) == 0:
        print('... no pdf files in {}'.format(dirname))
        return

    db = pd.DataFrame()
    db['local-url'] = flist

    years = []
    authors_s = []
    journals = []
    extras = []
    skip = False

    # file name check
    for f in sorted(flist):
        fname = f.split('/')[-1]
        tmp = fname.replace('.pdf','').split('-')
        extra = ''

        if len(tmp) < 3:
            print('... change fname: YEAR-AUTHOR-JOURNAL {}'.format(fname))
            skip = True
        elif len(tmp) > 3:
            if debug: print('... warning fname: YEAR-AUTHOR-JOURNAL {}'.format(fname))

            if tmp[-1] in ['1', '2', '3', '4', '5']:      # check duplicated same name, same journal, same year
                tmp[2] = '-'.join(tmp[2:-1])
                extra = tmp[-1]
            else:
                tmp[2] = '-'.join(tmp[2:])

        if not skip:
            years.append(tmp[0])
            authors_s.append(tmp[1].replace('_', '-'))
            journals.append(tmp[2].replace('_', ' '))
            extras.append(extra)

    db['year'] = years
    db['author1'] = authors_s
    db['journal'] = journals
    db['title'] = ''
    db['doi'] = ''
    db['keywords'] = [[]] * len(db)
    db['abstract'] = ''
    db['extra'] = extras
    db['sync'] = False

    return db


def update_files(dirname='.', debug=False):
    """ update pdf files with metadata """

    fdb = read_dir(dirname)

    for i in fdb.index[::-1]:
        print('[{}] {} - {} - {}'.format(i, fdb.at[i, "year"], fdb.at[i, "author1"], fdb.at[i, "journal"]))
        paper = Paper(fdb.at[i, "local-url"], debug=debug)
        print(paper)
        yesno = input("Continue? (skip/update/bibtex/quit/reload/abstract): ")
        if yesno in ["q", "quit", "Q", "Quit"]:
            break
        if yesno in ["u", "U", "update"]:
            paper.update()
        if yesno in ["b", "B", "bibtex"]:
            paper.bibtex()
            paper.update()
        if yesno in ["s", "S", "skip"]:
            continue
        if yesno in ["r", "R"]:
            if i < len(fdb.index)-1: i = i + 1
            continue
        if yesno in ["a", "A"]:
            paper.abstract()
            paper.update()


def build_filedb(dirname='.', debug=False, order='decr'):
    """ create database from pdf files """

    fdb = read_dir(dirname)

    if order == 'decr':
        idx_list = fdb.index[::-1]
    elif order == 'incr':
        idx_list = fdb.index
    else:
        idx_list = random.shuffle(fbd.index)

    for i in tqdm(idx_list):
        paper = Paper(fdb.at[i, "local-url"], debug=debug)

        fdb.at[i, "doi"] = paper.doi()
        paper.bibtex()
        fdb.at[i, "title"] = paper._title
        fdb.at[i, "keywords"] = paper.keywords()
        fdb.at[i, "abstract"] = paper.abstract(update=False)
        paper.update(force=True)

    return fdb
