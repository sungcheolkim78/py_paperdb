""" bibdb.py """

import os
import requests

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

from arxiv2bib import arxiv2bib


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

    print('... save to {}'.format(filename))


def get_bib(doi, asDict=True):
    """ get bib from crossref.org and arXiv.org """

    found = False

    # for arXiv:XXXX case
    if doi.lower()[:5] == "arxiv":
        doi = doi[6:]
        bib = arxiv2bib([doi])
        bib = bib[0].bibtex()
        found = True if len(bib) > 0 else False
    # for crossref
    else:
        bare_url = "http://api.crossref.org/"
        url = "{}works/{}/transform/application/x-bibtex"
        url = url.format(bare_url, doi)

        r = requests.get(url)
        found = False if r.status_code != 200 else True
        bib = r.content
        bib = str(bib, "utf-8")

    if not found:
        return found, ""

    if asDict:
        parser = BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = False
        parser.homogenise_fields = False

        bdb = bibtexparser.loads(bib, parser)
        entry = bdb.entries[0]

        return found, entry
    else:
        return found, str(bib, "utf-8")

