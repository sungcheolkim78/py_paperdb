""" py_paperdb """

import pandas as pd
import numpy as np
import os
import re
import tqdm
import pickle
import subprocess

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

from py_readpaper import Paper

import bibdb
import filedb

from utils import safe_pickle_dump

class PaperDB(object):
    """ paper database using pandas """

    def __init__(self, dirname='.', cache=True, debug=False):
        """ initialize database """

        self._debug = debug
        self._dirname = dirname
        self._bibfilename = '.paperdb.csv'
        self._metafname = './meta.p'
        self._tfidfname = './tfidf.p'
        self._simfname = './sim.p'
        self._ldafname = './lda.p'
        self._currentpaper = ''
        self._updated = False
        self._sim_dict = {}
        self._vocab = {}
        self._idf = []
        self._selection = set()

        if cache and os.path.exists(self._bibfilename):
            p = pd.read_csv(self._bibfilename, index_col=0)
            self._bibdb = bibdb.clean_db(p)
            if debug: print('... read from {}'.format(self._bibfilename))
        else:
            p = filedb.build_filedb(dirname=dirname, debug=debug)
            self._bibdb = bibdb.clean_db(p)
            self._bibdb.to_csv(self._bibfilename)
            if debug: print('... save to {}'.format(self._bibfilename))

    # view database

    def head(self, n=5, full=False, newest=False, items=[]):
        """ show old papers """

        if newest:
            temp = self._bibdb.sort_values('import_date', ascending=False)[:n]
            items.append('import_date')
        else:
            temp = self._bibdb[:n]

        if full and (len(items) == 0):
            return temp
        else:
            return quickview(temp, items=items)

    def tail(self, n=5, full=False, items=[]):
        """ show recently published papers """

        if full and (len(items) == 0):
            return self._bibdb[-n:]
        else:
            return quickview(self._bibdb[-n:], items=items)

    # search database

    def search_sep(self, year=0, author='', journal='', author1='', title='', doi=''):
        """ search database by separate search keywords """

        res = search(self._bibdb, year=year, author=author, journal=journal, author1=author1, title=title, doi=doi)

        if len(res.index) > 0:
            if len(res.index) > 10:
                yesno = input('Will you include all these selection? [Yes/No] ')
                if yesno in ['Yes', 'Y', 'y', 'yes']:
                    if self._debug: print('... save to selection: {}'.format(res.index.values))
                    self._selection = self._selection | set(res.index)
            else:
                if self._debug: print('... save to selection: {}'.format(res.index.values))
                self._selection = self._selection | set(res.index)

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

        if len(sindex) > 0:
            sindex = sorted(list(set(sindex)))
            self._selection = self._selection.union(set(sindex))

            return quickview(self._bibdb.iloc[sindex])

    def search_wrongname(self, columns=['doi', 'year', 'author1', 'journal']):
        """ find wrong file name from filedb """

        condition = (self._bibdb['has_bib'] == False)

        for c in columns:
            condition = condition | (self._bibdb[c] == '') | (self._bibdb[c] == 'nan')

        #condition = (self._bibdb['doi'] == '') | (self._bibdb['year'] == '') | (self._bibdb['author1'] == '') | (self._bibdb['journal'] == '') | (self._bibdb['author1'] == 'None') | (self._bibdb['has_bib'] == False)
        sindex = self._bibdb[condition].index

        print('... total {}/{} incorrect papers'.format(len(sindex), len(self._bibdb)))

        return quickview(self._bibdb.iloc[sindex])

    def search_new(self, n=10):
        """ print out recently added papers """

        return quickview(self._bibdb.sort_values(by='import_date')[-n:])

    def search_paper(self, paper, as_index=False):
        """ from Paper object find out position in bibdb """

        s_db = self._bibdb
        if paper.doi() != '':
            s_db = search(s_db, doi=paper.doi())
        elif paper.year() is not None:
            s_db = search(s_db, year=int(paper.year()))

        #paper.bibtex()

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
            idx = s_db.index[0]

            if paper._bib is not None:
                for keys in paper._bib.keys():
                    self._bibdb.at[idx, keys] = paper._bib.get(keys)

        self._bibdb.at[idx, 'local-url'] = paper._fname
        self._updated = True

        if as_index:
            return idx
        else:
            return quickview(self._bibdb.iloc[idx])

    # selection operations

    def selection_view(self):
        """ print selection """

        if len(self._selection) > 0:
            if self._debug: print('... # of selection: {}'.format(len(self._selection)))
            return quickview(self._bibdb.iloc[list(self._selection)])

    def selection_bibtex(self, n=-1):
        """ print bibtex items in selection """

        if len(self._selection) == 0:
            return
        if n == -1:
            n = len(self._selection)

        for c, i in enumerate(list(self._selection)):
            if c > n:
                return
            self.paper(i)
            self._currentpaper.bibtex()

    def selection_reset(self):
        """ reset all selections """

        yesno = input("Delete all selection? [Yes/No] ")
        if yesno in ['Y', 'Yes', 'y', 'yes']:
            self._selection = set()

    def selection_add(self, idxs):
        """ add papers by index """

        self._selection = self._selection | set(idxs)

    def selection_remove(self, idxs):
        """ remove papers by index """

        self._selection = self._selection - set(idxs)

    # control paper

    def paper(self, idx, exif=True):
        """ open pdf file in osx """

        try:
            filename = self._bibdb.at[idx, 'local-url']
            self._currentpaper = Paper(filename, exif=exif, debug=self._debug)
            return self._currentpaper
        except:
            print('... error reading: {}/{}'.format(idx, len(self._bibdb)))
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

    def export_bib(self, selection=False, bibfilename=None):
        """ save bibtex file and csv file """

        if selection:
            if bibfilename is None:
                bibfilename = 'selection.bib'
            bibdb.to_bib(self._bibdb.iloc[list(self._selection)], bibfilename)
            with open(bibfilename) as f:
                print(f.readlines())
        else:
            bibdb.to_bib(self._bibdb, self._bibfilename)

    def update(self, idx=-1):
        """ save database """

        if idx > -1:
            self._bibdb = filedb.update_filedb(self._bibdb, self._bibdb.at[idx, 'local-url'], debug=self._debug)
            self._updated = True

        if self._updated:
            print('... save database to {}'.format(self._bibfilename))
            self._bibdb.to_csv(self._bibfilename)

    def reload(self, update=True):
        """ re-read bibdb """

        self._bibdb = filedb.build_filedb(dirname=self._dirname, debug=debug)
        print('... save database to {}'.format(self._bibfilename))
        self._bibdb.to_csv(self._bibfilename)

    # recommender system

    def build_recommender(self, update=False):
        """ using text contents build vectorized representation of papers """

        pids = range(len(self._bibdb))

        if os.path.exists(self._tfidfname) and os.path.exists(self._metafname) and (not update):
            print('... read from {}, {}'.format(self._tfidfname, self._metafname))
            out = pickle.load(open(self._tfidfname, 'rb'))
            self._X = out['X']
            meta = pickle.load(open(self._metafname, 'rb'))
            self._vocab = meta['vocab']
            self._idf = meta['idf']
        else:
            print('... read all texts')
            corpus = []
            for i in tqdm.tqdm(pids):
                self.paper(i, exif=False)
                txt = '{}\n{}'.format(self._currentpaper.abstract(), self._currentpaper.contents(split=False, update=False))
                corpus.append(txt)

            # clean up text
            corpus = [ re.sub('\\n', ' ', str(x)) for x in corpus ]
            corpus = [ re.sub("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",'',str(x)) for x in corpus ]
            corpus = [ re.sub("(http://.*?\s)|(http://.*)",'',str(x)) for x in corpus ]
            corpus = [ x.replace("royalsocietypublishing", "") for x in corpus ]
            corpus = [ x.replace("annualreviews", "") for x in corpus ]
            corpus = [ x.replace("science reports", "") for x in corpus ]
            corpus = [ x.replace("nature publishing group", "") for x in corpus ]
            self.corpus = corpus

            # prepare vectorizer
            v = TfidfVectorizer(input='content',
                    encoding='utf-8', decode_error='replace', strip_accents='unicode',
                    lowercase=True, analyzer='word', stop_words='english',
                    token_pattern=r'(?u)\b[a-zA-Z_][a-zA-Z0-9_]+\b',
                    ngram_range=(1, 3), max_features = 5000,
                    norm='l2', use_idf=True, smooth_idf=True, sublinear_tf=True,
                    max_df=1.0, min_df=1)
            v.fit(corpus)
            self._X = v.transform(corpus)

            self._vocab = v.vocabulary_
            self._idf = v._tfidf.idf_

            # write full matrix out
            out = {}
            out['X'] = self._X
            print('... writing: {}'.format(self._tfidfname))
            safe_pickle_dump(out, self._tfidfname)

            # writing metatdata
            out = {}
            out['vocab'] = v.vocabulary_
            out['idf'] = v._tfidf.idf_
            out['pids'] = pids
            print('... writing: {}'.format(self._metafname))
            safe_pickle_dump(out, self._metafname)

        if os.path.exists(self._simfname) and (not update):
            print('... read from {}'.format(self._simfname))
            self._sim_dict = pickle.load(open(self._simfname, 'rb'))
        else:
            print("...precomputing nearest neighbor queries in batches...")
            #X = X.todense() # originally it's a sparse matrix
            X = self._X.todense().astype(np.float32)
            self._sim_dict = {}
            batch_size = 200
            for i in range(0,len(pids),batch_size):
                i1 = min(len(pids), i+batch_size)
                xquery = X[i:i1] # BxD
                ds = -np.asarray(np.dot(X, xquery.T)) #NxD * DxB => NxB
                IX = np.argsort(ds, axis=0) # NxB
                for j in range(i1-i):
                    self._sim_dict[pids[i+j]] = [pids[q] for q in list(IX[:50,j])]

                print('%d/%d...' % (i, len(pids)))

            print('... writing: {}'.format(self._simfname))
            safe_pickle_dump(self._sim_dict, self._simfname)

    def recommend_similar(self, idx=0, n=5, items=[]):
        """ recommend similar paper using feature matrix """

        if len(self._sim_dict) == 0:
            self.build_recommender()

        rec_list = self._bibdb.iloc[self._sim_dict[idx][:n]]
        return quickview(rec_list, items=items)

    def build_topiclist(self, n_com=20, max_iter=10, n_keys=8, update=False):
        """ make feature matrix using LDA """

        if os.path.exists(self._ldafname) and (not update):
            out = pickle.load(open(self._ldafname, 'rb'))
            self._lda = out['lda']
            self._topics = out['topics']
        else:
            if len(self._sim_dict) == 0:
                self.build_recommender()

            X = self._X.todense().astype(np.float32)
            lda = LatentDirichletAllocation(n_components=n_com,
                    learning_method='batch',
                    max_iter=max_iter, verbose=1,
                    n_jobs=-1, random_state=0)

            print("... computing decomposition matrix: n_com {}, max_iter {}".format(n_com, max_iter))
            paper_topics = lda.fit_transform(X)
            feature_names = sorted(list(self._vocab.keys()))

            for topic_idx, topic in enumerate(lda.components_):
                msg = 'Topic [{}]: '.format(topic_idx)
                msg += ', '.join([feature_names[i] for i in topic.argsort()[:-n_keys-1:-1]])
                print(msg)

            # writing lda result
            out = {}
            out['lda'] = paper_topics
            out['topics'] = lda.components_
            print('... writing: {}'.format(self._ldafname))
            safe_pickle_dump(out, self._ldafname)
            self._lda = paper_topics
            self._topics = lda.components_

    def recommend_topic(self, tid=0, n=5, n_com=20, n_keys=8, items=[]):
        """ recommend papers using decomposition """

        if len(self._lda) == 0:
            self.build_topiclist(n_com=ncom, n_keys=n_keys)

        topic = self._topics[tid]
        feature_names = sorted(list(self._vocab.keys()))
        msg = " ".join([feature_names[i] for i in topic.argsort()[:-n_keys:-1]])
        print('Topic {}: {}'.format(tid, msg))

        idxlist = np.argsort(self._lda[:, tid])[::-1]
        lda_list = self._bibdb.iloc[idxlist[:n]]
        return quickview(lda_list, items=items)

    def word_list(self):
        """ print feature names """

        if self._vocab is None:
            self.build_recommender()

        feature_names = sorted(list(self._vocab.keys()))
        v = pd.DataFrame(self._idf, index=feature_names, columns=['idf'])
        return v.sort_values(by='idf')


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

    views = ["year", "author1", "author", "title", "journal", "doi"]
    if (len(items) > 0) and add:
        views = views + items
    elif (len(items) > 0) and not add:
        views = items

    #print('.... columns: {}'.format(views))

    return pd_db[views]


