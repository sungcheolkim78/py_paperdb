"""
filedb.py

update pdf file metadata
"""

import os
import datetime
import platform
import glob
import pandas as pd
from tqdm import tqdm

from py_readpaper import Paper


# file db structure
# local-url, year, author1, journal, title, doi, keywords, abstract, extra, sync

def read_dir(dirname='.', debug=False):
    """ from file list and filenames build panda db not using Paper library (fast) """

    flist = sorted(glob.glob(dirname + '/*.pdf'))
    if len(flist) == 0:
        print('... no pdf files in {}'.format(dirname))
        return

    colnames = ['year', 'author1', 'author', 'journal', 'title', 'doi', 'pmid', 'pmcid', 'keywords',
            'gensim', 'abstract', 'local-url', 'rating', 'has_bib', 'import_date', 'extra', 'sync']

    db = pd.DataFrame(columns=colnames)
    db['local-url'] = flist

    years = []
    authors_s = []
    journals = []
    extras = []
    skip = False

    # file name check
    for f in flist:
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
                if debug: print('{} | {} | {} | {}'.format(tmp[0], tmp[1].replace('_', '-'), tmp[2].replace('_', ' '), extra))
            else:
                tmp[2] = '-'.join(tmp[2:])
                if debug: print('{} | {} | {}'.format(tmp[0], tmp[1].replace('_', '-'), tmp[2].replace('_', ' ')))

        if not skip:
            years.append(int(tmp[0]))
            authors_s.append(tmp[1].replace('_', '-'))
            journals.append(tmp[2].replace('_', ' '))
            extras.append(extra)

    db['year'] = years
    db['author1'] = authors_s
    db['journal'] = journals
    db['extra'] = extras

    return db


def build_filedb(dirname='.', debug=False):
    """ create database from pdf files """

    fdb = read_dir(dirname)

    col_list = ["author", "author1", "journal", "title", "doi", "pmid", "pmcid", "abstract" ]

    for i in tqdm(fdb.index):
        paper = Paper(fdb.at[i, "local-url"], debug=debug, exif=False)

        for c in col_list:
            fdb.at[i, c] = paper._bib.get(c, '')

        fdb.at[i, "year"] = paper._bib.get("year", 0)
        fdb.at[i, "keywords"] = paper._bib.get("keywords", [])
        fdb.at[i, "rating"] = paper._bib.get("rating", 0)
        fdb.at[i, "has_bib"] = paper._exist_bib
        fdb.at[i, "import_date"] = datetime.datetime.fromtimestamp(os.path.getmtime(fdb.at[i, "local-url"]))
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

    col_list = ["author", "author1", "journal", "title", "doi", "pmid", "pmcid", "abstract" ]
    for c in col_list:
        fdb.at[idx, c] = paper._bib.get(c, '')

    fdb.at[idx, "year"] = paper._bib.get("year", 0)
    fdb.at[idx, "keywords"] = paper._bib.get("keywords", [])
    fdb.at[idx, "rating"] = paper._bib.get("rating", 0)
    fdb.at[idx, "has_bib"] = paper._exist_bib
    fdb.at[idx, "import_date"] = datetime.datetime.fromtimestamp(os.path.getmtime(paper._fname))

    return fdb


def check_files(dirname='.', globpattern='*.pdf', count=False, debug=False):
    """ check pdf files and match bib data """

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

        p = Paper(f, debug=debug)
        p.interactive_update()


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime
