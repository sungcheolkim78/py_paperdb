""" py_paperdb """

import pandas as pd
import glob
import os

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

from pdf_read import convertPDF


def build_pd(dirname='.'):
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
    error_flag = False

    # file name check
    for f in flist:
        fname = f.split('/')[-1]
        tmp = fname.replace('.pdf','').split('-')

        if len(tmp) < 3:
            print('... change fname: YEAR-AUTHOR-JOURNAL {}'.format(fname))
            error_flag = True
        elif len(tmp) > 3:
            print('... warning fname: YEAR-AUTHOR-JOURNAL {}'.format(fname))

            if tmp[-1] in ['1', '2', '3', '4', '5']:      # check duplicated same name, same journal, same year
                tmp[2] = ''.join(tmp[2:-1])
            else:
                tmp[2] = ''.join(tmp[2:])

        if not error_flag:
            years.append(tmp[0])
            authors_s.append(tmp[1].replace('_', '-'))
            journals.append(tmp[2].replace('_', ' '))

    db['year'] = years
    db['author_s'] = authors_s
    db['journal'] = journals

    return db


def read_txtpdf(fdb, i, trim=True):
    fname = fdb.iloc[i]['local-url']
    txt = convertPDF(fname, maxpages=1)

    if trim:
        txt = txt.replace('\n\n\n\n', 'C_RETURN').replace('\n\n\n', 'C_RETURN').replace('\n\n', 'C_RETURN').replace('\n', '').replace('C_RETURN', '\n\n')
        txt = txt.replace('\n\n\n', '\n')
        txt = txt.replace('\n\n \n\n', '\n')
        txt = txt.replace('\n.\n', '\n')

    return txt


def read_paperdb(filename, frombib=False):
    """ read bib file or csv file """

    fname_csv = ''.join(filename.split('.')[:-1]) + '.csv'
    if (not frombib) and os.path.exists(fname_csv):
        print('... read from {}'.format(fname_csv))
        p = pd.read_csv(fname_csv, index_col=0)
        p = p.fillna('')
        return p

    bib = read_bib(filename)
    return from_bib(bib, filename=fname_csv)

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


def to_bib(pd_db, filename):
    """ save panda bib records into file """

    items = pd_db.astype(str).to_dict("records")

    db = BibDatabase()

    db.entries = items

    writer = BibTexWriter()
    with open(filename, 'w') as bibfile:
        bibfile.write(writer.write(db))


def from_bib(bib_db, filename=""):
    """ read bib file and convert it to panda db and save to csv """

    p = pd.DataFrame.from_dict(bib_db.entries)

    p['read'] = p['read'].fillna('False')
    p = p.fillna('')
    if "uri" in p.columns:
        p['doi'] = p['uri'].str.slice(31, -1)
        p = p.drop(columns=['uri'])

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
        p = p.drop(columns=['bdsk-file-1', 'bdsk-url-1', 'bdsk-url-2'])

    if filename != "":
        newname = ''.join(filename.split('.')[:-1])+'.csv'
        print('... save to {}'.format(newname))
        p.to_csv(newname)

    return p


def search(pd_db, year=0, author='', journal='', author1=''):
    """ search panda database by keywords """

    if "author1" not in pd_db.columns:
        pd_db["author1"] = [ x.split(' and ')[0] for x in pd_db['author'].values ]

    if year != 0:
        if (pd_db.year.dtype == 'int') and isinstance(year, int):
            db = pd_db.loc[pd_db['year'] == year]
        else:
            db = pd_db.loc[pd_db.year.str.contains(str(year))]
    else:
        db = pd_db

    if author != '':
        db = db.loc[db.author.str.contains(author)]

    if author1 != '':
        db = db.loc[db.author1.str.contains(author1+",")]

    if journal != '':
        db = db.loc[db.journal.str.contains(journal)]

    return db


def quickview(pd_db):
    """ view paperdb with essential columns """

    return pd_db[["year", "author", "title", "journal"]]

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

    #return pd_db
