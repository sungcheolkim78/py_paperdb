"""
filedb.py

update pdf file metadata
"""

import os
import glob
import random
import pandas as pd
import numpy as np
from tqdm import tqdm, tqdm_notebook

from py_readpaper import Paper
from py_readpaper import read_bib
from py_readpaper import print_bib


# file db structure
# local-url, year, author1, journal, title, doi, keywords, abstract, extra, sync

def read_dir(dirname='.', debug=False):
    """ from file list and filenames build panda db """

    flist = sorted(glob.glob(dirname + '/*.pdf'))
    if len(flist) == 0:
        print('... no pdf files in {}'.format(dirname))
        return

    db = pd.DataFrame()

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
            years.append(int(tmp[0]))
            authors_s.append(tmp[1].replace('_', '-'))
            journals.append(tmp[2].replace('_', ' '))
            extras.append(extra)

    db['year'] = years
    db['author1'] = ''
    db['author'] = ''
    db['journal'] = ''
    db['title'] = ''
    db['doi'] = ''
    db['pmid'] = ''
    db['pmcid'] = ''
    db['keywords'] = [[]] * len(db)
    db['gensim'] = [[]] * len(db)
    db['abstract'] = ''
    db['local-url'] = flist
    db['rating'] = ''
    db['read'] = False
    db['has_bib'] = False
    db['month'] = ''
    db['volume'] = ''
    db['booktitle'] = ''
    db['extra'] = extras
    db['sync'] = False

    return db


def build_filedb(dirname='.', debug=False):
    """ create database from pdf files """

    fdb = read_dir(dirname)

    col_list = ["month", "volume", "author", "author1", "journal", "booktitle", "title", "doi", "pmid", "pmcid", "abstract" ]

    for i in tqdm(fdb.index):
        paper = Paper(fdb.at[i, "local-url"], debug=debug, exif=False)

        for c in col_list:
            fdb.at[i, c] = paper._bib.get(c, '')

        fdb.at[i, "year"] = paper._bib.get("year", 0)
        fdb.at[i, "keywords"] = paper._bib.get("keywords", [])
        fdb.at[i, "read"] = paper._bib.get("read", False)
        fdb.at[i, "rating"] = paper._bib.get("rating", 0)
        fdb.at[i, "has_bib"] = paper._exist_bib
        #fdb.at[i, "gensim"] = paper.keywords_gensim()
        #fdb.at[i, "sync"] = True

    return fdb


def update_filedb(fdb, filename, debug=False):
    """ update filedb for one file """

    find_file = fdb[fdb['local-url'] == filename]

    if len(find_file) == 0:
        print('... can not find file: {}'.format(filename))
        return

    idx = find_file.index[0]
    if debug: print(fdb.iloc[idx])

    paper = Paper(fdb.at[idx, "local-url"], debug=debug, exif=False)

    col_list = ["month", "volume", "author", "author1", "journal", "booktitle", "title", "doi", "pmid", "pmcid", "abstract" ]
    for c in col_list:
        fdb.at[idx, c] = paper._bib.get(c, '')

    fdb.at[idx, "year"] = paper._bib.get("year", 0)
    fdb.at[idx, "keywords"] = paper._bib.get("keywords", [])
    fdb.at[idx, "read"] = paper._bib.get("read", False)
    fdb.at[idx, "rating"] = paper._bib.get("rating", 0)
    fdb.at[idx, "has_bib"] = paper._exist_bib

    return fdb


def check_files(dirname='.', globpattern='*.pdf', masterdbname=None, count=False):
    """ check pdf files and match bib data """

    if masterdbname is None:
        master_db = None
    else:
        master_db = read_bib(masterdbname, cache=True)

    flist = glob.glob(dirname + '/' + globpattern)

    missing_flist = []
    for f in flist:
        base, fname = os.path.split(os.path.abspath(f))
        bibfname = os.path.join(base, dirname+'/.'+fname.replace('.pdf', '.bib'))
        if not os.path.exists(bibfname):
            missing_flist.append(f)

    if count:
        print('... total {}/{} missing bib files'.format(len(missing_flist), len(flist)))
        return

    for i, f in enumerate(missing_flist):
        base, fname = os.path.split(os.path.abspath(f))
        bibfname = os.path.join(base, dirname+'/.'+fname.replace('.pdf', '.bib'))

        print('[CF][{}/{}] ... no bib file: {}'.format(i, len(missing_flist), bibfname))
        p = Paper(f)
        print_bib(p.bib())

        # confirm search
        yesno = input("[CF] Want to serach bib (bibdb/doi/title/skip/quit): ")
        if yesno in ["b", "B", "bibdb", '1']:
            p.search_bib(bibdb=master_db, threshold=0.6)
        elif yesno in ["d", "D", "doi", '2']:
            p.download_bib(cache=False)
        elif yesno in ["t", "title", '3']:
            p.doi(checktitle=True)
        elif yesno in ['q', 'Q', '5']:
            break

        # confirm update
        if yesno not in ["s", "S", "skip", '4']:
            yesno = input("[CF] Continue update (yes/no/quit): ")
        else:
            yesno = 'y'

        if yesno in ['q', 'Q', 'quit', 'Quit', '3']:
            break
        elif yesno in ['yes', 'y', 'Yes', 'Y', '1']:
            p.update(force=True)
        else:
            continue

