#!/usr/local/bin/python3
'''
proc_newfiles.py - check all pdf files and sync with corresponding .bib file and internal pdf meta information

Usage: $./proc_newfiles.py
'''

import py_paperdb
import os
import glob

dst_dir = '../papers'

# update pdf files

py_paperdb.check_files('.', debug=False)

# confirm to move files

yesno = input("Continue to move files? (yes/no) ")
if yesno in ['y', 'Y']:
    pdflist = glob.glob('./*.pdf')
    for f in pdflist:
        os.rename(f, dst_dir+'/'+f)

    biblist = glob.glob('./.*.bib')
    for f in biblist:
        os.rename(f, dst_dir+'/'+f)

    #print('... clean up bib files')
    #biblist = glob.glob('./*.bib')
    #for f in biblist: os.remove(f)
    #biblist = glob.glob('./*.csv')
    #for f in biblist: os.remove(f)

    print('... update paper database')
    p = py_paperdb.PaperDB(dirname='../papers', cache=False)
    p._updated=True
    p.update()

