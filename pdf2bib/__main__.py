#!/usr/bin/env python
# Python script that READS PDF files in current folder, gets DOI and queries for metadata
# Metadata is stored in bibtex file and file name is changed
# Google citations are added to the bibtex file as an additinal field
#import subprocess
#from urllib.request import urlopen
from PyPDF2 import PdfFileReader
import re
import sys
import argparse
import os.path
import glob
import shutil
import crossref_commons.retrieval
import readline
import unicodedata

parser = argparse.ArgumentParser(
    description='Get Metadata and organize PDF files.',
    epilog='(c) Jorge Ramirez - jorge.ramirez@upm.es - ETSII - UPM (2015)')
parser.add_argument('-b', '--bibtexfile', help='output bibtex file name (default=bibtex.bib)', default='bibtex.bib', nargs=1)
parser.add_argument('-v', '--verbose', help='Write debug information to stdout', action='store_true')
parser.add_argument('-a', '--add', help='Ask for missing/incorrect doi (default=false)', action='store_true')
parser.add_argument('filelist', nargs='+')

args = parser.parse_args()

full_paths = [os.path.join(os.getcwd(), path) for path in args.filelist]
files = []
for path in full_paths:
    if os.path.isfile(path):
        files.append(path)
    else:
        lll=glob.glob(path)
        for f in lll:
            files.append(f)


ofilename = args.bibtexfile
if os.path.isfile(ofilename):
    print ("BibTeX File already exists! Creating BACKUP!")
    shutil.copy(ofilename, ofilename+'.bak')        
    #sys.exit();
#bibtexfile = open (ofilename, 'w', encoding="utf-8")
bibtexfile = open (ofilename, 'w', encoding="latin1", errors='replace')

def debug(leading_text, variable):
    if args.verbose:
        print (leading_text, variable)

def strip_accents(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

def rlinput(prompt, prefill=''):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    finally:
        readline.set_startup_hook()

def getdoifrompdf(filename):
    # EXTRACT DOI FROM PDF  
    doi_re = re.compile('(10[.][0-9]{4,}[^\s"/<>]*/[^\s"<>]+)')
    pdffile=open(filename, "rb")
    inputPDF = PdfFileReader(pdffile)
    npages = inputPDF.numPages
    debug('npages',npages)
    DOI=""
    try:
        for i in range(npages):
            debug('Page',i)
            text = inputPDF.getPage(i).extractText()
            #debug('text',text)
            m = doi_re.search(text)
            debug('M',m)
            if m!=None:
                debug('GROUP',m.groups())
                DOI = m.groups()[0]
                break
    except: 
        print("Could not get the DOI from the PDF")
    pdffile.close()
    if DOI=="":
        print("DOI not found")
        DOI = input("Enter DOI manually: ")
        
    return DOI

def processfile(DOI, filename):
    try:
        A=crossref_commons.retrieval.get_publication_as_json(DOI)
    except: 
        print("It looks like the DOI " + DOI + " does not exist")
        DOI = rlinput("Input DOI: ", DOI)
        A=crossref_commons.retrieval.get_publication_as_json(DOI)
        
    SPACER='        '
    author1=A['author'][0]['family']
    year=str(A['published']['date-parts'][0][0])
    bibkey=strip_accents(author1)+'_'+year

    # ATTEMPT TO WRITE FILE (CHANGE FILENAME AND BIBKEY IF NECESSARY)
    FNAME=filename.split(os.sep)
    FOLDER=os.sep.join(FNAME[0:len(FNAME)-1])
    OLDFNAME=FNAME[-1]
    #print(FNAME)
    NEWFNAME=bibkey+'.pdf'
    if NEWFNAME!=OLDFNAME:
        FILENAME=FOLDER+os.sep+bibkey+'.pdf'
        if os.path.isfile(FILENAME):
            print ('File '+FILENAME+' already exists!')
            done=0
            ci=ord('a')-1
            while not done:
                ci+=1
                c=chr(ci)
                FILENAME=FOLDER+os.sep+bibkey+c+'.pdf'
                print ('Trying with '+FILENAME)
                if os.path.isfile(FILENAME):
                    done=0
                else:
                    done=1
                    bibkey=bibkey+c

        done=0
        while not done:
            try:
                os.rename(filename, FILENAME)
                done=1
            except PermissionError:
                key = input('FILE MUST BE OPEN IN ANOTHER APPLICATION. CLOSE IT AND PRESS RETURN...')

    else:
        print('PDF File already has the correct name')

    # WRITE BIBTEX ENTRY
    bibtexfile.write('@article{'+bibkey+',\n')
    doi=A['DOI']
    bibtexfile.write(SPACER+'doi = {'+ doi + '},\n')
    bibtexfile.write(SPACER+'year = {' + year + '},\n')
    #journal=A['container-title'][0]
    #print(SPACER+'journal = ', journal + ',')
    shortjournal=A['short-container-title'][0]
    bibtexfile.write(SPACER+'journal = {'+ shortjournal + '},\n')
    bibtexfile.write(SPACER+'publisher = {' + A['publisher'] + '},\n')
    if 'volume' in A.keys():
        bibtexfile.write(SPACER+'volume = {'+ A['volume'] + '},\n')
    if 'issue' in A.keys():
        bibtexfile.write(SPACER+'number = {'+ A['issue'] + '},\n')
    authorstring=''
    for i,aut in enumerate(A['author']):
        if i>0:
            authorstring+=' and '
        authorstring+=aut['given'] + ' ' + aut['family']
    bibtexfile.write(SPACER+'author = {' + authorstring + '},\n')
    bibtexfile.write(SPACER+'title = {'+ A['title'][0] + '},\n')
    bibtexfile.write(SPACER+'file = '+ bibkey + '.pdf:' + bibkey + '.pdf:PDF,\n')
    bibtexfile.write(SPACER+'citations = '+ str(A['is-referenced-by-count'])+'\n')
    bibtexfile.write('}\n\n')

    bibtexfile.flush()


def main():

    for filename in files:
        print ('*** Processing '+filename)
        DOI=getdoifrompdf(filename)
        if len(DOI)>0:
            processfile(DOI, filename)
        else:
            print ('DOI not found for FILE:'+filename)
            if args.add: 
                DOI=input("Introduce DOI manually: ")
                debug('DOI', DOI)
                processfile(DOI, filename)
            else:
                print ('Skipping '+filename)
    bibtexfile.close()


if __name__ == "__main__":
    main()
