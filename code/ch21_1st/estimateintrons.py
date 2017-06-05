#!/usr/bin/env python

import argparse
import os
import sqlite3

from Bio import SeqIO, SeqRecord, Seq
from Bio.Blast.Applications import NcbiblastnCommandline as blastn
from Bio import AlignIO
from Bio.Blast import NCBIXML
from Bio.Align.Applications import ClustalwCommandline

AT_DB_FILE = 'AT.db'
BLAST_EXE = '~/opt/ncbi-blast-2.6.0+/bin/blastn'
BLAST_DB = '~/opt/ncbi-blast-2.6.0+/db/TAIR10'
CLUSTALW_EXE = '../../clustalw2'

def allgaps(seq):
    """Return a list with tuples containing all gap positions
       and length. seq is a string."""
    i = 0
    gaps = []
    indash = False
    for c in seq:
        if indash is False and c=='-':
            c_ini = i
            indash = True
            dashn = 0
        elif indash is True and c=='-':
            dashn += 1
        elif indash is True and c!='-':
            indash = False
            gaps.append((c_ini,dashn+1))
        i += 1
    return gaps

def iss(record):
    """Infer Splicing Sites from a FASTA file full of EST
    sequences"""

    usersid = record.id
    userseq = record.seq
    blastn_cline = blastn(cmd=BLAST_EXE, query=args.input_file, db=BLAST_DB,
                        evalue='1e-10', outfmt=5, num_descriptions='1', num_alignments='1', out='outfile.xml')
    blastn_cline()
    #result, err = NCBIStandalone.blastall(blast_exe, "blastn",
    #              blast_db, f_name, expectation='1e-10',
    #              descriptions='1', alignments='1')

    #with open('outfile.xml','w') as of:
    #    of.write(result.read())
    b_record = NCBIXML.read(open('outfile.xml'))
    title = b_record.alignments[0].title
    sid = title[title.index(' ')+1:title.index(' |')]
    # Polarity information of returned sequence.
    # 1 = normal, -1 = reverse.
    frame = b_record.alignments[0].hsps[0].frame[1]

    # Run the SQLite query
    ###NO!!
    conn = sqlite3.connect(AT_DB_FILE)
    c = conn.cursor()
    res_cur = c.execute('SELECT CDS, FULL_SEQ from seq WHERE ID=?',
                        (sid,))
    cds, full_seq = res_cur.fetchone()
    if cds=='':
        print('There is no matching CDS')
        exit()

    # Check sequence polarity.
    if frame==1:
        seqCDS = SeqRecord.SeqRecord(Seq.Seq(cds),id=sid+'-CDS'
                                 ,name="",description="")
        fullseq = SeqRecord.SeqRecord(Seq.Seq(full_seq), id=sid+'-SEQ'
                                 ,name="",description="")
    else:
        seqCDS = SeqRecord.SeqRecord(
            Seq.Seq(cds).reverse_complement(),id=sid+'-CDS',
            name="",description="")
        fullseq = SeqRecord.SeqRecord(
            Seq.Seq(full_seq).reverse_complement(),id=sid+'-SEQ',
            name="",description="")

    # Create a tuple with the user sequence and both AT sequences.
    allseqs = (record,seqCDS,fullseq)

    with open('foralig.txt','w') as trifh:
        # Write the file with the three sequences.
        SeqIO.write(allseqs, trifh, 'fasta')

    # Do the alignment:
    outfilename = usersid + '.aln'
    cline = ClustalwCommandline(CLUSTALW_EXE,
                                infile = 'foralig.txt',
                                outfile = outfilename,
                                )
    cline()

    # Walk over all aligned sequences and look for query sequence
    for seq in AlignIO.read(outfilename, 'clustal'):
        if usersid in seq.id:
            seqstr = seq.seq.tostring()
            gaps = allgaps(seqstr.strip('-'))
            break

    print("Original sequence:",usersid)
    print("\nBest match in AT CDS:",sid)

    i = 0
    acc = 0
    for gap in gaps:
        i += 1
        print("Intron #%s: Start at position %s, length %s"
              %(i,gap[0]-acc,gap[1]))
        acc += gap[1]

    print('\n'+seqstr.strip('-'))
    print('\nAlignment file: '+usersid+'.aln\n')

description = 'XXX'
parser = argparse.ArgumentParser(description=description)
ifh = 'Fasta formated file with sequence to search for introns'
parser.add_argument('input_file', help=ifh)
args = parser.parse_args()

## DEBUG: f_name='/mnt/hda2/bio/t3.txt'
seqhandle = open(args.input_file)
records = SeqIO.parse(seqhandle, 'fasta')

for record in records:
    iss(record)
