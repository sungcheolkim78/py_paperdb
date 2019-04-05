"""
Functions for PDF parsing tools and utils
"""

import urllib
import io

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage


def convertPDF(pdf_path, codec='utf-8', maxpages=0):
    """
    Takes path to a PDF and returns the text inside it as string

    pdf_path: string indicating path to a .pdf file. Can also be a URL starting
              with 'http'
    codec: can be 'ascii', 'utf-8', ...
    returns string of the pdf, as it comes out raw from PDFMiner
    """

    if pdf_path[:4] == 'http':
        print('first downloading %s ...' % (pdf_path,))
        urllib.urlretrieve(pdf_path, 'temp.pdf')
        pdf_path = 'temp.pdf'

    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)

    fp = open(pdf_path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    caching = True
    pagenos = set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages,
                                  password=password,
                                  caching=caching,
                                  check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue()

    fp.close()
    device.close()
    retstr.close()

    return text

