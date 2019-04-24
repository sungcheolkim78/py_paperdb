""" py_paperdb """

import pandas as pd
import os
import subprocess

from py_readpaper import Paper

from bibdb import read_bib, to_bib, read_paperdb, read_bibfiles
from bibdb import find_bib_dict, compare_bib_dict
from bibdb import merge_items
from bibdb import clean_db

from filedb import read_dir, build_filedb, check_files


class PaperDB(object):
    """ paper database using pandas """

    def __init__(self, dirname='.', cache=True, debug=False):
        """ initialize database """

        self._debug = debug
        self._dirname = dirname
        self._bibfilename = '.paperdb.csv'
        self._currentpaper = ''
        self._updated = False

        if cache:
            if os.path.exists(self._bibfilename):
                p = pd.read_csv(self._bibfilename, index_col=0)
                self._bibdb = clean_db(p)
                if debug: print('... read from {}'.format(self._bibfilename))
            else:
                self._bibdb = build_filedb(dirname=dirname, debug=debug)
                self._bibdb.to_csv(self._bibfilename)
                if debug: print('... save to {}'.format(self._bibfilename))
        else:
            p = build_filedb(dirname=dirname, debug=debug)
            self._bibdb = clean_db(p)

    # view database

    def head(self, n=5, full=False, items=[]):
        """ show old items """

        if full and (len(items) == 0):
            return self._bibdb[:n]
        else:
            res = quickview(self._bibdb, items=items)
            return res[:n]

    def tail(self, n=5, full=False, items=[]):
        """ show recent items """

        if full and (len(items) == 0):
            return self._bibdb[-n:]
        else:
            res = quickview(self._bibdb, items=items)
            return res[-n:]

    # search database

    def search_sep(self, year=0, author='', journal='', author1='', title='', doi=''):
        """ search database by separate search keywords """

        res = search(self._bibdb, year=year, author=author, journal=journal, author1=author1, title=title, doi=doi)

        return quickview(res)

    def search_all(self, sstr=None, columns=None):
        """ search searchword for all database """

        if sstr is None:
            print('... add search string')
            os.exit(1)
        if columns is None:
            columns = ['title', 'abstract', 'author', 'keywords', 'doi', 'local-url']
        if 'keywords' in columns:
            self._bibdb['keywords_csv'] = [ ','.join(x) for x in self._bibdb['keywords'] ]
            columns.remove('keywords')
            columns.append('keywords_csv')

        sindex = []
        for c in columns:
            res = self._bibdb[self._bibdb[c].str.contains(sstr)].index
            if len(res) > 0:
                sindex.extend(res)

        sindex = sorted(list(set(sindex)))
        return quickview(self._bibdb.iloc[sindex])

    def search_wrongname(self):
        """ find wrong file name from filedb """

        condition = (self._bibdb['year'] == '') | (self._bibdb['author1'] == '') | (self._bibdb['journal'] == '') | (self._bibdb['author1'] == 'None') | (self._bibdb['has_bib'] == False)
        sindex = self._bibdb[condition].index

        return quickview(self._bibdb.iloc[sindex])

    def search_paper(self, paper):
        """ from Paper object find out position in bibdb """

        s_db = self._bibdb
        if paper.doi() is not None:
            s_db = search(s_db, doi=paper._doi)
        elif paper._year is not None:
            s_db = search(s_db, year=int(paper._year))

        paper.bibtex()

        # multiple match
        if len(s_db) > 1:
            if self._debug: print('... multiple matches')
            return quickview(s_db)

        # no match
        if len(s_db) == 0:
            if self._debug: print('... add to bibdb')
            if paper._bib is None:
                item = {'year': paper._year, 'journal': paper._journal, 'author': paper._author, \
                        'author1': paper._author1, 'abstract': paper._abstract, 'keywords': paper._keywords }
            else:
                item = paper._bib

            self._bibdb = self._bibdb.append(item, ignore_index=True)
            idx = len(self._bibdb) - 1

        # exact match
        if len(s_db) == 1:
            if self._debug: print('... update bibdb')
            idx = s_db.index

            if paper._bib is not None:
                for keys in paper._bib.keys():
                    self._bibdb.at[idx, keys] = paper._bib.get(keys)

        self._bibdb.at[idx, 'local-url'] = paper._fname
        self._updated = True

        return quickview(self._bibdb.iloc[idx])

    # control paper

    def paper(self, idx):
        """ open pdf file in osx """

        try:
            filename = self._bibdb.at[idx, 'local-url']
            self._currentpaper = Paper(filename)
            return self._currentpaper
        except:
            print('... out of range: {}'.format(len(self._bibdb)))
            return False

    def open(self, idx=-1):
        """ open pdf file in osx """

        if isinstance(self.paper(idx), Paper):
            self._currentpaper.open()
        else:
            cmd = ["Open", self._bibfilename]
            subprocess.call(cmd)

    def readpaper(self, idx=-1, n=10):
        """ open paper in text mode """

        if isinstance(self.paper(idx), Paper):
            return self._currentpaper.head(n=n)

    def item(self, idx):
        """ show records in idx """

        # update using paper's information
        if isinstance(self.paper(idx), Paper):
            self._updated = True
            self._currentpaper.save_bib()

            for k, i in self._currentpaper._bib.items():
                self._bibdb.at[idx, k] = i
            self._bibdb.at[idx, "has_bib"] = True

        return self._bibdb.iloc[idx]

    # manage database

    def export_bib(self, update=False):
        """ save bibtex file and csv file """

        to_bib(self._bibdb, self._bibfilename)

    def update(self):
        """ save database """

        if self._updated:
            self._bibdb.to_csv(self._bibfilename)

    def reload(self, update=True):
        """ re-read bibdb """

        self._bibdb = build_filedb(dirname=dirname, debug=debug)
        self._bibdb.to_csv(self._bibfilename)


def search(pd_db, year=0, author='', journal='', author1='', title='', doi='', byindex=False):
    """ search panda database by keywords """

    if ("author1" not in pd_db.columns) and ("author" in pd_db.columns):
        pd_db["author1"] = [ x.split(' and ')[0] for x in pd_db['author'].values ]

    if year != 0:
        pd_db.loc[:, 'year'] = pd_db.loc[:, 'year'].astype(int)
        db = pd_db.loc[pd_db['year'] == year]
    else:
        db = pd_db

    def _search_item(db, column, value):
        if (value != '') and (column in db.columns):
            db[column].fillna('', inplace=True)
            return db.loc[db[column].str.contains(value)]
        else:
            return db

    db = _search_item(db, "author", author)
    db = _search_item(db, "author1", author1)
    db = _search_item(db, "journal", journal)
    db = _search_item(db, "title", title)
    db = _search_item(db, "doi", doi)

    if byindex:
        return db.index
    else:
        return db


def quickview(pd_db, items=[], add=True):
    """ view paperdb with essential columns """

    views = ["year", "author1", "author", "title", "journal"]
    if (len(items) > 0) and add:
        views = views + items
    elif (len(items) > 0) and not add:
        views = items

    #print('.... columns: {}'.format(views))

    return pd_db[views]


