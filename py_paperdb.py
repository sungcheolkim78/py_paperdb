""" py_paperdb """

import pandas as pd
import os
import subprocess

import py_readpaper
from py_readpaper import find_author1

from bibdb import read_bib, to_bib, read_paperdb, find_duplicate
from filedb import read_dir, update_files, build_filedb


class PaperDB(object):
    """ paper database using pandas """

    def __init__(self, dirname='.', bibfilename='master_db.bib', update=False, debug=False):
        """ initialize database """

        self._debug = debug
        self._dirname = dirname
        self._bibfilename = bibfilename
        self._filedb = read_dir(dirname=dirname, debug=debug)
        self._bibdb = read_paperdb(bibfilename, update=update)
        self._currentpaper = ''
        self._updated = False

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

    def get_paper(self, idx=-1, filedb=False):
        """ open pdf file in osx """

        if idx > -1:
            if filedb:
                filename = self._filedb.at[idx, 'local-url']
            else:
                filename = self._bibdb.at[idx, 'local-url']
            if os.path.exists(filename):
                self._currentpaper = py_readpaper.Paper(filename)
                return True
            else:
                print('... not found: {}'.format(filename))
                return False

        return False

    def open(self, idx=-1, filedb=False):
        """ open pdf file in osx """

        if self.get_paper(idx, filedb=filedb):
            self._currentpaper.open()
        else:
            cmd = ["Open", self._bibfilename]
            subprocess.call(cmd)

    def readpaper(self, idx=-1, n=10, filedb=False):
        """ open paper in text mode """

        if self.get_paper(idx, filedb=filedb):
            return self._currentpaper.head(n=n)

    def item(self, idx, filedb=False):
        """ show records in idx """

        if filedb:
            return self._filedb.iloc[idx]
        else:
            return self._bibdb.iloc[idx]

    def merge(self, idx1, idx2):
        """ merge two items """

        print("[{}] ....".format(idx1))
        print(self.item(idx1))
        print("[{}] ....".format(idx2))
        print(self.item(idx2))

    def sync_db(self):
        """ confirm all files have bibtex information """

        for i in self._filedb.index[::-1]:
            res = self._bibdb[self._bibdb['local-url'] == self._filedb.at[i, 'local-url']]
            if len(res) == 1:
                self._filedb.at[i, "sync"] = True
            else:
                # show filedb information
                paper = py_readpaper.Paper(self._filedb.at[i, "local-url"])
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

    def find_doi(self, idx):
        if self.get_paper(idx):
            return self._currentpaper.doi()
        else:
            return self._bibdb.at[idx, 'doi']

    def find_keywords(self, idx, method='find', **kwargs):
        if self.get_paper(idx):
            if method == 'find':
                return self._currentpaper.keywords()
            else:
                return self._currentpaper.keywords_gensim(**kwargs)
        else:
            return self._bibdb.at[idx, 'keywords']

    def update_doi(self, idx, doi="", force=False):
        """ update doi item """

        old_doi = self._bibdb.at[idx, 'doi']
        new_doi = doi if doi != "" else self.find_doi(idx)

        print('old doi: {}\nnew doi: {}'.format(old_doi, new_doi))
        yesno = input("Will you change? [(y)es/(n)o]") if not force else "y"
        if yesno in ["Yes", "yes", "y", "Y"]:
            self._bibdb.at[idx, "doi"] = new_doi
            if self.get_paper(idx):
                self._currentpaper._doi = new_doi
            self._updated = True

    def update_keywords(self, idx, keywords="", force=False):
        """ update keyword item """

        old_kw = self._bibdb.at[idx, 'keywords']
        if keywords == "":
            new_kw = self.find_keywords(idx)
        else:
            new_kw = keywords

        print('old keywords: {}\nnew keywords: {}'.format(old_kw, new_kw))
        if len(new_kw) > 0:
            yesno = input("Will you change? [(y)es/(n)o]") if not force else "y"
        else:
            yesno = "n"

        if yesno in ["Yes", "yes", "y", "Y"]:
            if len(new_kw) > 0:
                self._bibdb.at[idx, "keywords"] = ', '.join(new_kw)
                self._updated = True

    def addby_filedoi(self, idx, doi=""):
        """ add bib item into bibdb using doi """

        found = True
        if self.get_paper(idx, filedb=True):
            item = self._currentpaper.bibtex(doi=doi)
        if item == "":
            found = False

        if found:
            self._bibdb = self._bibdb.append(item, ignore_index=True)
            self._bibdb.at[len(self._bibdb)-1, "local-url"] = self._filedb.at[idx, "local-url"]
            self._bibdb.at[len(self._bibdb)-1, "rating"] = 0.0
            self._bibdb = self._bibdb.fillna('')
            self._filedb.at[idx, "doi"] = doi
            self._updated = True

        if self._debug and found:
            print('=== filedb ' + '='*60)
            print(self._filedb.iloc[idx])
            print('=== bib db ' + '='*60)
            print(self._bibdb.iloc[len(self._bibdb)-1])

    def save(self, update=False):
        """ save bibtex file and csv file """

        if update or self._updated:
            to_bib(self._bibdb, self._bibfilename)
            self._bibdb.to_csv(self._bibfilename.replace(".bib", ".csv"))
        else:
            print('... no changes')

    def reload(self, update=True):
        """ re-read filedb and bibdb """

        self._filedb = read_dir(dirname=self._dirname)
        self._bibdb = read_paperdb(self._bibfilename, update=update)

    def remove_item(self, idx):
        """ remove item by idx """

        self._updated = True
        return self._bibdb.drop(self._bibdb.index[idx], inplace=True)

    def search_sep(self, year=0, author='', journal='', author1=''):
        """ search database by separate search keywords """

        res = search(self._bibdb, year=year, author=author, journal=journal, author1=author1)

        return quickview(res)

    def search_all(self, sstr=None, columns=None):
        """ search searchword for all database """

        if sstr is None:
            print('... add search string')
            os.exit(1)
        if columns is None:
            columns = ['title', 'abstract', 'author', 'year', 'keywords']

        sindex = []
        for c in columns:
            res = self._bibdb[self._bibdb.title.str.contains(sstr)].index
            if len(res) > 0:
                sindex.extend(res)

        sindex = list(set(sindex))
        return quickview(self._bibdb[self._bibdb.index[sinde]])


def search(pd_db, year=0, author='', journal='', author1='', title='', keywords='', byindex=False):
    """ search panda database by keywords """

    if ("author1" not in pd_db.columns) and ("author" in pd_db.columns):
        pd_db["author1"] = [ x.split(' and ')[0] for x in pd_db['author'].values ]

    if year != 0:
        pd_db['year'] = pd_db['year'].astype(int)
        db = pd_db.loc[pd_db['year'] == year]
    else:
        db = pd_db

    def _search_item(db, column, value):
        if (value != '') and (column in db.columns):
            return db.loc[db[column].str.contains(value)]
        else:
            return db

    db = _search_item(db, "author", author)
    db = _search_item(db, "author1", author1)
    db = _search_item(db, "journal", journal)
    db = _search_item(db, "title", title)
    db = _search_item(db, "keywords", keywords)

    if byindex:
        return db.index
    else:
        return db


def quickview(pd_db, items=[], add=True):
    """ view paperdb with essential columns """

    views = ["year", "author", "title", "journal"]
    if (len(items) > 0) and add:
        views = views + items
    elif (len(items) > 0) and not add:
        views = items

    #print('.... columns: {}'.format(views))

    return pd_db[views]


