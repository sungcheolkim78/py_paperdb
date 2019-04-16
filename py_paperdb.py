""" py_paperdb """

import pandas as pd
import os
import subprocess

from py_readpaper import Paper

from bibdb import read_bib, to_bib, read_paperdb, read_bibfiles
from bibdb import find_bib_dict, compare_bib_dict
from bibdb import merge_items

from filedb import read_dir, build_filedb, check_files


class PaperDB(object):
    """ paper database using pandas """

    def __init__(self, dirname='.', bibfilename='master_db.bib', update=False, debug=False):
        """ initialize database """

        self._debug = debug
        self._dirname = dirname
        self._bibfilename = bibfilename
        self._filedb = read_dir(dirname=dirname, debug=debug)
        self._bibdb = build_filedb(dirname=dirname, debug=debug, cache=cache)
        self._currentpaper = ''
        self._updated = False

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
            columns = ['title', 'abstract', 'author', 'keywords', 'doi']
        if "keywords" in columns:
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

        self._bibdb.at[idx, "local-url"] = paper._fname
        self._updated = True

        return quickview(self._bibdb.iloc[idx])

    # control paper

    def get_paper(self, idx):
        """ open pdf file in osx """

        try:
            filename = self._bibdb.at[idx, 'local-url']
            self._currentpaper = Paper(filename)
            return self._currentpaper
        except:
            num = len(self._bibdb) if filedb else len(self._bibdb)
            print('... out of range: {}'.format(num))
            return False

    def open(self, idx=-1, filedb=False):
        """ open pdf file in osx """

        if isinstance(self.get_paper(idx, filedb=filedb), Paper):
            self._currentpaper.open()
        else:
            cmd = ["Open", self._bibfilename]
            subprocess.call(cmd)

    def readpaper(self, idx=-1, n=10, filedb=False):
        """ open paper in text mode """

        if isinstance(self.get_paper(idx, filedb=filedb), Paper):
            return self._currentpaper.head(n=n)

    def item(self, idx):
        """ show records in idx """

        return self._bibdb.iloc[idx]

    # manage database

    def merge_duplicates(self, threshold=0.5):
        """ find and merge duplicates """

        count = 0
        index_set = set(self._bibdb.index)

        while index_set:
            i = index_set.pop()
            item1 = self._bibdb.loc[i]

            sameindex, scores = find_bib_dict(self._bibdb, item1, index=True, threshold=threshold)
            if self._debug: print('... check [{}] - scores: {}'.format(i, scores))

            if len(sameindex) > 1:
                if self._debug: print('... [{}] found duplicates {}'.format(i, sameindex))
                for j in sameindex:
                    success, self._bibdb = merge_items(self._bibdb, i, j, debug=self._debug)
                    if success:
                        index_set.discard(j)
                        count = count + 1

        print('... total {} duplicates!'.format(count))

    def sync_db(self):
        """ confirm all files have bibtex information """

        for i in self._filedb.index[::-1]:
            res = self._bibdb[self._bibdb['local-url'] == self._filedb.at[i, 'local-url']]
            if len(res) == 1:
                self._filedb.at[i, "sync"] = True
            else:
                # show filedb information
                paper = Paper(self._filedb.at[i, "local-url"])
                i_year = int(self._filedb.at[i, "year"])
                i_author1 = self._filedb.at[i, "author1"]
                i_journal = self._filedb.at[i, "journal"]
                print("... filedb [{}] : {} - {} - {} - {} - {}".format(i, i_year, i_author1, i_journal, paper._author, paper._title))

                # multiple links
                if len(res) > 1:
                    print('... multiple links')
                    print(quickview(res, items=["year", "author1", "journal", "title"], add=False))
                    continue

                # search by year and author1
                idx1 = search(self._bibdb, year=i_year, author1=i_author1, byindex=True)
                idx2 = search(self._bibdb, year=i_year, journal=i_journal, byindex=True)
                idx = list(set(list(idx1) + list(idx2)))
                res = self._bibdb.iloc[idx]

                if len(res) > 0:
                    print('... search by year and author')
                    print(quickview(res, items=["year", "author1", "journal", "title"], add=False))

                    link_idx = input("Enter correct bib database index: [(s)kip/(q)uit/(a)dd] ")
                    if link_idx == 's':
                        continue
                    elif link_idx == 'q':
                        break
                    elif link_idx == 'a':
                        self.addby_filedoi(i, paper.doi())
                    else:
                        self._filedb.at[i, "sync"] = True
                        self.update_localurl(int(link_idx), fdb_idx=i)
                else:
                    print('... no records')
                    self.addby_filedoi(i, paper.doi())

    def update_localurl(self, idx, fdb_idx=-1):
        """ connect local-url from filedb into bibdb """

        if (fdb_idx > -1) and (fdb_idx < len(self._filedb)):
            self._bibdb.at[idx, "local-url"] = self._filedb.at[fdb_idx, "local-url"]

            if self._bibdb.at[idx, "journal"] in ["TODO", ""]:
                self._bibdb.at[idx, "journal"] = self._filedb.at[fdb_idx, "journal"]

            self._updated = True

            if self._debug:
                print('=== filedb ' + '='*60)
                print(self._filedb.iloc[fdb_idx])
                print('=== bib db ' + '='*60)
                print(self._bibdb.iloc[idx])

    def save(self, update=False):
        """ save bibtex file and csv file """

        if update or self._updated:
            to_bib(self._bibdb, self._bibfilename)
            self._bibdb.to_csv(self._bibfilename.replace(".bib", ".csv"))
        else:
            print('... no changes')

    def reload(self, update=True):
        """ re-read filedb and bibdb """

        self._bibdb = build_filedb(dirname=dirname, debug=debug)


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
            db[column] = db[column].fillna('')
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


