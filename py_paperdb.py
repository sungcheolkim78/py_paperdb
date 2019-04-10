""" py_paperdb """

import pandas as pd
import glob
import os
import subprocess

import py_readpaper
from bibdb import read_bib, to_bib

class PaperDB(object):
    """ paper database using pandas """

    def __init__(self, dirname='.', bibfilename='master_db.bib', update=False):
        """ initialize database """

        self._dirname = dirname
        self._bibfilename = bibfilename
        self._filedb = read_dir(dirname=dirname)
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

        for i in self._filedb.index:
            res = self._bibdb[self._bibdb['local-url'].str.contains(self._filedb.at[i, 'local-url'])]
            if len(res) == 1:
                self._filedb.at[i, "sync"] = True
            else:
                # show filedb information
                i_year = int(self._filedb.at[i, "year"])
                i_author1 = self._filedb.at[i, "author_s"]
                i_journal = self._filedb.at[i, "journal"]
                print("... filedb [{}] : {} - {} - {}".format(i, i_year, i_author1, i_journal))

                # multiple links
                if len(res) > 1:
                    print('... multiple links')
                    print(quickview(res, items=["year", "author1", "journal"], add=False))
                    continue

                # search by year and author1
                res = search(self._bibdb, year=i_year, author1=i_author1)
                if len(res) > 0:
                    print('... search by year and author')
                    print(quickview(res, items=["year", "author1", "journal"], add=False))

                    link_idx = input("Enter correct bib database index: [(s)kip/(q)uit] ")
                    if link_idx == 's':
                        continue
                    elif link_idx == 'q':
                        break
                    else:
                        self._filedb.at[i, "sync"] = True
                        self.update_localurl(int(link_idx), fdb_idx=i)

                else:
                    # search by year and journal
                    res = search(self._bibdb, year=i_year, journal=i_journal)
                    if len(res) > 0:
                        print('... search by year and journal')
                        print(quickview(res, items=["year", "author1", "journal"], add=False))

                        link_idx = input("Enter correct bib database index: [(s)kip/(q)uit] ")
                        if link_idx == 's':
                            continue
                        elif link_idx == 'q':
                            break
                        else:
                            self._filedb.at[i, "sync"] = True
                            self.update_localurl(int(link_idx), fdb_idx=i)

                    else:
                        print('... no records')
                        self.add_by_doi(i)

    def update_localurl(self, idx, fdb_idx=-1, verb=True):
        """ connect local-url from filedb into bibdb """

        if fdb_idx > -1:
            try:
                self._bibdb.at[idx, "local-url"] = self._filedb.at[fdb_idx, "local-url"]
                self._updated = True
            except:
                print('... {}, {} out of range {}, {}'.format(idx, fdb_idx, len(self._bibdb), len(self._filedb)))

        if verb:
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

    def addby_filedoi(self, idx, doi="", verb=True):
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

        if verb and found:
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
        res = search(self._bibdb, year=year, author=author, journal=journal, author1=author1)
        return quickview(res)

def read_dir(dirname='.'):
    """ from file list and filenames build panda db """

    flist = sorted(glob.glob(dirname + '/*.pdf'))
    if len(flist) == 0:
        print('... no pdf files in {}'.format(dirname))
        return 0

    db = pd.DataFrame()
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
            print('... warning fname: YEAR-AUTHOR-JOURNAL {}'.format(fname))

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
    db['author_s'] = authors_s
    db['journal'] = journals
    db['extra'] = extras
    db['doi'] = ''
    db['sync'] = False

    return db


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


def search(pd_db, year=0, author='', journal='', author1=''):
    """ search panda database by keywords """

    if "author1" not in pd_db.columns:
        pd_db["author1"] = [ x.split(' and ')[0] for x in pd_db['author'].values ]

    if year != 0:
        pd_db['year'] = pd_db['year'].astype(int)
        db = pd_db.loc[pd_db['year'] == year]
    else:
        db = pd_db

    if author != '':
        db = db.loc[db.author.str.contains(author)]

    if author1 != '':
        db = db.loc[db.author1.str.contains(author1)]

    if journal != '':
        db = db.loc[db.journal.str.contains(journal)]

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


def check_filedb(pd_db, f_db):
    """ check file database and update local-url field """

    count = 0
    for i in range(len(f_db['year'])):
        f_res = f_db.iloc[i]
        p_res = search(pd_db, year=int(f_res['year']), author1=f_res['author_s'])

        if len(p_res['year']) > 0:
            found = 0

            if (len(p_res['year']) == 1) and (p_res.iloc[0]['journal'] == ''):
                found = 1

            for e in p_res['journal'].values:
                if e.lower().find(f_res['journal'].lower()) > -1:
                    found = found + 1

            if found == 0:
                print('... check {}: {} - {} - {}'.format(i, f_res['year'], f_res['author_s'], f_res['journal']))
                return quickview(p_res)

            if found > 1:
                if len(set(p_res['title'])) == 1:
                    found = 1
                else:
                    print('... check {}: {} - {} - {}'.format(i, f_res['year'], f_res['author_s'], f_res['journal']))
                    return quickview(p_res)

            if found == 1:
                pd_db.at[p_res.index[0],'local-url'] = f_res['local-url']
                pd_db.at[p_res.index[0],'file'] = f_res['local-url']
                count = count + 1
        else:
            print('... check {}: {} - {} - {}'.format(i, f_res['year'], f_res['author_s'], f_res['journal']))

    print('... total files: {}'.format(len(f_db['year'])))
    print('... matched files: {}'.format(count))


def find_duplicate(pd_db):
    """ find duplicated items """
    return 0


def find_author1(authors, options='last'):
    """ find first author's name """

    names = authors.split(' and ')

    n1 = names[0]

    if n1.find(',') > -1:
        firstname = ' '.join(n1.split(',')[1:])
        lastname = n1.split(',')[0]
    else:
        firstname = ' '.join(n1.split(' ')[:-1])
        lastname = n1.split(' ')[-1]

    if options == 'last':
        return lastname
    elif options == 'first':
        return firstname
    else:
        return firstname + ', ' + lastname

