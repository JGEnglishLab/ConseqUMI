#!/usr/bin/python

import sys
import argparse
import os
import umi_extractor as ue
import umi_binner as ub
import gui
import subprocess
from timeit import default_timer as timer
import time
import re
from Bio import SeqIO
import numpy as np
import random
from Levenshtein import distance
import pandas as pd
from collections import defaultdict, Counter
from os.path import exists
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from statistics import mean, median
from Bio.Align import PairwiseAligner
import subprocess
from io import StringIO
from consensus_generators.ConsensusContext import ConsensusContext


def main():

    parser = set_command_line_settings()
    args = vars(parser.parse_args())
    check_for_invalid_input(parser, args)
    if args['command'] == 'gui' or args['command'] is None:  # Default to GUI
        gui.main()
        return
    print('\nOutput Directory Created: ' + args['output'])
    startTime = timer()
    '''
    print('\nUMI Extraction')
    UMIExtractor = ue.UMIExtractor()
    print('----> ' + stringify_time_since_start(startTime, timer()) + ' setting adapter objects', flush=True)
    with open(args['adapters'], 'r') as adapterFile: adapters = [adapter.rstrip() for adapter in adapterFile.readlines()]
    UMIExtractor.set_universal_front_and_reverse_linked_adapters(adapters[0], adapters[1], adapters[2], adapters[3])
    files = [args['input']+file for file in os.listdir(args['input'])]
    print('----> ' + stringify_time_since_start(startTime, timer()) + ' identifying adapter start indices', flush=True)
    UMIExtractor.identify_and_set_front_and_reverse_adapter_start_indices_from_file(files)
    print('----> ' + stringify_time_since_start(startTime, timer()) + ' extracting UMI sequences', flush=True)
    excludedCount = UMIExtractor.extract_umi_and_sequences_from_files(files, args['output'])
    print('----> ' + stringify_time_since_start(startTime, timer()) + ' lines excluded because adapters didn\'t match: ' + str(excludedCount), flush=True)
    print('\nStarcode Binning')
    print('----> ' + stringify_time_since_start(startTime, timer()) + ' begin umi1 process', flush=True)
    run_starcode(args['output']+ 'umi1.txt', args['output']+ 'starcode1.txt')

    print('----> ' + stringify_time_since_start(startTime, timer()) + ' begin umi2 process', flush=True)
    run_starcode(args['output']+ 'umi2.txt', args['output']+ 'starcode2.txt')

    print('----> ' + stringify_time_since_start(startTime, timer()) + ' remove chimeras', flush=True)
    ub.remove_chimeras_from_umi_pairs(args['output']+ 'starcode1.txt', args['output']+ 'starcode2.txt', args['output']+ 'starcode_without_chimeras.txt')
    print('----> ' + stringify_time_since_start(startTime, timer()) + ' bin sequences by UMI pair', flush=True)
    ub.bin_sequences_by_umi_pair(args['output'] + 'seq.fq', args['output']+ 'starcode_without_chimeras.txt', args['minimumReads'])
    #'''
    args['output'] = '/Users/calebcranney/Documents/Projects/longread_umi_python/test/data/delete/newConsensus_delete-20221116-151545/delete/'
    if args['benchmarkClusters']:
        print('----> ' + stringify_time_since_start(startTime, timer()) + ' bootstrapping', flush=True)
        dfs = []
        binFiles = [args['output']+x for x in os.listdir(args['output']) if re.match('seq_bin\d+\.fq', x)]
        #for i in range(len(binFiles)): print(str(i) + ': ' + str(sorted(binFiles)[i]))
        for binFile in sorted(binFiles):
            tempDf = benchmark_binned_sequences(args['output'], binFile, iteration = 1)
            tempDf.to_csv('.'.join(binFile.split('.')[:-1]) + '_benchmark.csv', index = False)
            dfs.append(tempDf)
        df = pd.concat(dfs)
        print('----> ' + stringify_time_since_start(startTime, timer()) + ' writing benchmarking output', flush=True)
        df.to_csv(args['oldOutput'] + 'benchmark.csv', index=False)
    else:

        print('\nConsensus Sequence Generation')
        print('----> ' + stringify_time_since_start(startTime, timer()) + ' obtaining consensus sequences', flush=True)

        binFiles = sorted([args['output']+x for x in os.listdir(args['output']) if re.match('seq_bin\d+\.fq', x)])
        pattern = '(\d+)'
        records = consensus_pipeline(args['consensusAlgorithm'], args['output'], binFiles, pattern)
        consensusFile = 'consensus_' + args['consensusAlgorithm'] + '.fasta'
        print('----> ' + stringify_time_since_start(startTime, timer()) + ' writing consensus output', flush=True)
        with open(args['oldOutput'] + consensusFile, "w") as output_handle:
            SeqIO.write(records, output_handle, "fasta")
        if args['variants']:
            print('----> ' + stringify_time_since_start(startTime, timer()) + ' obtaining variant sequences', flush=True)
            superBinFiles = cluster_consensus_sequences(args['output'], args['oldOutput'] + 'consensus.fasta', binFiles)
            superPattern = '(_super[_\d]+)'
            finalRecords = consensus_pipeline(args['consensusAlgorithm'], args['output'], superBinFiles, superPattern)
            with open(args['oldOutput'] + 'variants.fasta', "w") as output_handle:
                SeqIO.write(finalRecords, output_handle, "fasta")
            print('----> ' + stringify_time_since_start(startTime, timer()) + ' writing variant output', flush=True)

def stringify_time_since_start(start, end):
    return time.strftime("%H:%M:%S", time.gmtime(end-start))

def find_average_aligned_score(candidateSeq, binRecords):
    binSeqs = [str(record.seq) for record in binRecords]
    aligner = PairwiseAligner()
    aligner.mismatch_score = -1
    aligner.open_gap_score = -1
    aligner.extend_gap_score = -0.5
    scores = []
    score_to_ids = []
    for i in range(len(binSeqs)):
        #if i % 100 == 0: print(i)
        alignments = aligner.align(candidateSeq, binSeqs[i])
        scores.append(alignments[0].score)
        score_to_ids.append([binRecords[i].id, alignments[0].score])
    return mean(scores), score_to_ids

def find_aligned_differences(seq1, seq2):

    aligner = PairwiseAligner()
    alignments = aligner.align(seq1,seq2)
    indices = alignments[0].aligned
    a_idx, b_idx = list(indices[0]), list(indices[1])
    a_idx.insert(0, (0,0))
    b_idx.insert(0, (0,0))
    a_idx.append((len(seq1),len(seq1)))
    b_idx.append((len(seq2),len(seq2)))

    diffs = []

    for i in range(len(a_idx)-1):
        start = a_idx[i][1]
        end = a_idx[i+1][0]
        insert = seq2[b_idx[i][1]:b_idx[i+1][0]]
        if start == end and len(insert)==0: continue
        diffs.append((start, end, insert))
    return diffs

def update_candidate_seq_by_common_diffs(candidateSeq, binRecords, cutoff_percent = None, binNum = None):
    diffs = []
    for binRecord in binRecords:
        tempDiffs = find_aligned_differences(candidateSeq, str(binRecord.seq))
        tempDiffs = [(x[0], x[1], x[2], binNum, binRecord.id) for x in tempDiffs]
        diffs.extend(tempDiffs)
    finalSeq = candidateSeq[:]

    if cutoff_percent:
        cutoff = len(binRecords) * cutoff_percent
        commonDiffs = sorted([key for key,value in Counter(diffs).items() if value > cutoff],reverse=True)
        for diff in commonDiffs:
            start, end, insert, _, _ = diff
            finalSeq = finalSeq[:start] + insert + finalSeq[end:]
    else:
        tempDiffs = [(x[0],x[1],x[2]) for x in diffs]
        most_common_diff = Counter(tempDiffs).most_common(1)[0][0]
        #print(most_common_diff)
        start, end, insert = most_common_diff
        finalSeq = finalSeq[:start] + insert + finalSeq[end:]
    return finalSeq, diffs

def generate_consensus_sequence_from_file(binFile, cutoff_percent=None):
    binPattern = "seq_bin(\d+)\.fq"
    binPattern = re.compile(binPattern)
    binNum = binPattern.search(binFile).group(1)
    binRecords = [record for record in SeqIO.parse(binFile, "fastq")]
    return generate_consensus_sequence(binRecords, cutoff_percent, binNum)

def generate_consensus_sequence(binRecords, cutoff_percent, binNum=None):
    diffs = []
    binSeqs = [str(record.seq) for record in binRecords]
    #print(len(binSeqs))
    #for key, value in sorted(Counter([len(x) for x in binSeqs]).items(), key=lambda x:x[1]):
    #    print(f'{key}, {value}')
    refSeq = find_initial_consensus(binSeqs)
    #print(f'refSeq: {refSeq}')
    if cutoff_percent: return update_candidate_seq_by_common_diffs(refSeq, binRecords, cutoff_percent, binNum)
    #print('skip cutoff')
    bestScore = -np.inf
    candidateSeq = refSeq[:]
    counter = 0

    curScore, score_to_ids = find_average_aligned_score(candidateSeq, binRecords)
    #scoreDf = pd.DataFrame(score_to_ids, columns = ['seqID','score'])
    #scoreDf.to_csv(f'score_to_ids{counter}.csv', index=False)
    while curScore >= bestScore:
        #print(counter)
        bestScore = curScore
        tempSeq, diffs = update_candidate_seq_by_common_diffs(candidateSeq, binRecords, cutoff_percent, binNum)
        #diffDf = pd.DataFrame(diffs, columns = ['start','end','insert','binNum','seqID'])
        #diffDf.to_csv(f'differences{counter}.csv', index=False)

        curScore, score_to_ids = find_average_aligned_score(tempSeq, binRecords)
        if curScore >= bestScore: candidateSeq = tempSeq
        counter += 1
        #scoreDf = pd.DataFrame(score_to_ids, columns = ['seqID','score'])
        #scoreDf.to_csv(f'score_to_ids{counter}.csv', index=False)
        #print(curScore)
        if counter > 15: return candidateSeq
        #if counter > 2: return candidateSeq, diffs, True
    #return candidateSeq, diffs, False
    return candidateSeq

def align_seqs(seqs):
    '''
    if len(seqs) > 100:
        lengths = [len(seq) for seq in seqs]
        occurence_count = Counter(lengths)
        most_freq_length = occurence_count.most_common(1)[0][0]
        seqs = [seq for seq in seqs if len(seq) > most_freq_length - 5 and len(seq) < most_freq_length + 5]
        if len(seqs) > 100: seqs = random.choices(seqs, k=100)
    #'''
    seq_str = ''
    for seq in seqs:
        seq_str += '>' + seq.description + '\n'
        seq_str += str(seq.seq) + '\n'
    #print('start mafft')
    child = subprocess.Popen(['mafft', '--quiet', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    child.stdin.write(seq_str.encode())
    child_out = child.communicate()[0].decode('utf8')
    #print('end mafft')
    seq_ali = list(SeqIO.parse(StringIO(child_out), 'fasta'))
    child.stdin.close()
    return seq_ali



def find_consensus_mafft(binPath, fast=True):
    #pattern = '(\d+)'
    #binPattern = "seq_bin" + pattern + "\.fq"
    #binPattern = re.compile(binPattern)
    #binNum = binPattern.search(binPath).group(1)
    records = [record for record in SeqIO.parse(binPath, "fastq")]

    aligned = align_seqs(records)
    arr = pd.DataFrame([list(str(seq.seq)) for seq in aligned])

    if fast:
        common = arr.mode()
        return ''.join([x.upper() for x in common.iloc[0] if x != '-'])

    seqCharacters = []
    for (columnName, columnData) in arr.iteritems():
        c = Counter(columnData.values).most_common()
        if len(c) > 1 and c[0][0] == '-' and abs(c[0][1] - c[1][1]) < 10: seqCharacters.append(c[1][0])
        else: seqCharacters.append(c[0][0])
    return ''.join([x.upper() for x in seqCharacters if x != '-'])


def lamassemble_pipeline_returns_consensus_record(binPath):
    child = subprocess.Popen(['lamassemble',
                              '/Users/calebcranney/Documents/Projects/lamassemble/train/promethion.mat',
                              binPath,
                              '--end',
                              '-g60'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    #child.stdin.write(seq_str.encode())
    child_out = child.communicate()[0].decode('utf8')
    seq_ali = list(SeqIO.parse(StringIO(child_out), 'fasta'))
    child.stdin.close()
    return seq_ali



def custom_pipeline(outputDir, binFiles, pattern):
    binPattern = "seq_bin" + pattern + "\.fq"
    binPattern = re.compile(binPattern)
    records = []
    allDiffs = []
    for i in range(len(binFiles)):
    #for i in range(1):
        binFile = binFiles[i]
        binNum = binPattern.search(binFile).group(1)
        consensusSeq = generate_consensus_sequence_from_file(binFile)
        #consensusSeq, _, _ = generate_consensus_sequence_from_file(binFile)
        #consensusSeq, diffs, b = generate_consensus_sequence_from_file(binFile)
        #if b: break
        #allDiffs.extend(diffs)
        seqRecord = SeqRecord(Seq(consensusSeq),id=binNum)
        records.append(seqRecord)
        if i % 1 == 0: print(f'{i+1} / {len(binFiles)}', flush=True)
    #diffDf = pd.DataFrame(allDiffs, columns = ['start','end','insert','binNum','seqID'])
    #diffDf.to_csv(outputDir + 'differences.csv', index=False)

    return records

def mafft_pipeline(outputDir, binFiles, pattern):
    binPattern = "seq_bin" + pattern + "\.fq"
    binPattern = re.compile(binPattern)
    records = []
    allDiffs = []
    for i in range(len(binFiles)):
        binFile = binFiles[i]
        binNum = binPattern.search(binFile).group(1)
        consensusSeq = find_consensus_mafft(binFile)
        seqRecord = SeqRecord(Seq(consensusSeq),id=binNum)
        records.append(seqRecord)
        if i % 1 == 0: print(f'{i+1} / {len(binFiles)}', flush=True)
    return records

def lamassemble_pipeline(outputDir, binFiles, pattern):
    binPattern = "seq_bin" + pattern + "\.fq"
    binPattern = re.compile(binPattern)
    records = []
    allDiffs = []
    for i in range(len(binFiles)):
        binFile = binFiles[i]
        binNum = binPattern.search(binFile).group(1)
        consensusSeq = str(lamassemble_pipeline_returns_consensus_record(binFile)[0].seq)
        seqRecord = SeqRecord(Seq(consensusSeq),id=binNum)
        records.append(seqRecord)
        if i % 1 == 0: print(f'{i+1} / {len(binFiles)}', flush=True)
    return records


def medaka_pipeline(outputDir, binFiles, pattern):
    binPattern = "seq_bin" + pattern + "\.fq"
    binPattern = re.compile(binPattern)
    for binFile in binFiles:
        seq = run_medaka_on_file(outputDir, binFile)
        if seq == 'XXXXX': print('empty sequence: ' + binPattern.search(binFile).group(1)); continue
        os.rename(outputDir + 'consensus.fasta', outputDir + 'consensus' + binPattern.search(binFile).group(1) + '.fasta')

    consPattern = re.compile("consensus" + pattern + "\.fasta")

    consensusFiles = [outputDir+x for x in sorted(os.listdir(outputDir)) if re.match('consensus' + pattern + '.fasta',x)]
    records = []
    for file in consensusFiles:
        for record in SeqIO.parse(file, "fasta"): record.id = consPattern.search(file).group(1); records.append(record)
    return records

def consensus_pipeline(option, outputDir, binFiles, pattern):
    cc = ConsensusContext(option)
    if option == 'pairwise' or option == 'lamassemble' or option == 'medaka': return cc.generate_consensus_sequences(binFiles)
    if option == 'mafft': return mafft_pipeline(outputDir, binFiles, pattern)

def adjust_all_string_lengths(strs, buffer_length):
    max_length = len(max(strs, key = len))
    strs = [x.ljust(max_length+buffer_length) for x in strs]
    return strs

def initialize_consensus_output_string(strs, excerpt_length):
    tempList = [x[:excerpt_length] for x in strs]
    final = max(set(tempList), key = tempList.count)
    return final

def find_next_character(subStrings, tempPattern):
    pattern = re.compile(tempPattern + '.')
    baseCountDict = defaultdict(list)
    all_characters = []
    for x in subStrings:
        r = pattern.search(x)
        if r: baseCountDict[r.group(0)[-1]].append(r.start(0)); all_characters.append(r.group(0)[-1])
    c = Counter(all_characters)
    percent_benchmark = .2
    benchmark = int(len(subStrings)*percent_benchmark)
    common = c.most_common()
    if len(common) > 1 and common[1][1] > benchmark:
        min_val = min([median(baseCountDict[x[0]]) for x in common[:2]])
        res = [x[0] for x in common[:2] if median(baseCountDict[x[0]]) == min_val]
        return res[0]
    return c.most_common()[0][0]

def find_initial_consensus(strs, excerpt_length = 10, buffer_length = 20):
    strs = adjust_all_string_lengths(strs, buffer_length)
    final = initialize_consensus_output_string(strs, excerpt_length)
    for i in range(len(strs[0])-buffer_length):
        subStrings = [x[i:i+buffer_length] for x in strs]
        tempPattern = final[-excerpt_length:]
        nex = find_next_character(subStrings, tempPattern)
        final += nex
    return final.strip(' ')

def run_medaka_on_file(outputDir, binFile, bc = False):
    records = [record for record in SeqIO.parse(binFile, "fastq")]
    draftFile = '.'.join(binFile.split('.')[:-1])+'_draft.fq'
    consSequence_count = defaultdict(int)
    returnSequence = 'XXXXX'
    for i in range(len(records)):
        seqStrs = [str(record.seq) for record in records]
        for i in range(len(seqStrs)):
            while len(seqStrs[i]) != 0 and seqStrs[i][-1] == 'A': seqStrs[i] = seqStrs[i][:-1]

        for i in range(len(seqStrs)):
            if len(seqStrs[i]) == 0: return returnSequence
        draftSeq = find_initial_consensus(seqStrs)
        consSeqs = [draftSeq]
        while len(consSeqs) < 5:
            draftSeq = SeqRecord(Seq(consSeqs[-1]),id='draft seq')
            with open(draftFile, "w") as output_handle: SeqIO.write([draftSeq], output_handle, "fasta")


            process = subprocess.Popen(['medaka_consensus',
             '-i', binFile,
             '-d', draftFile,
             '-o', outputDir])
            stdout, stderr = process.communicate()
            print(f'Draft File: {draftFile}')
            print(f'Bin File: {binFile}')
            if exists(outputDir + 'consensus.fasta'): consensusRecords = [record for record in SeqIO.parse(outputDir + 'consensus.fasta', "fasta")]
            else: return returnSequence
            os.remove(outputDir + 'calls_to_draft.bam')
            os.remove(outputDir + 'calls_to_draft.bam.bai')
            os.remove(outputDir + 'consensus_probs.hdf')
            os.remove(draftFile)
            os.remove(draftFile + '.mmi')


            if len(consensusRecords) == 0:
                os.remove(outputDir + 'consensus.fasta')
                return returnSequence

            consensusSequence = str(consensusRecords[0].seq)
            if bc: os.remove(outputDir + 'consensus.fasta')
            if consSeqs[-1] == consensusSequence: return consensusSequence
            consSeqs.append(consensusSequence)
        return consensusSequence
        consSequence_count[consensusSequence] += 1
        if consSequence_count[consensusSequence] >= 3: break

    return consensusSequence

def benchmark_binned_sequences(outDir, binPath, iteration = 100):
    records = [record for record in SeqIO.parse(binPath, "fastq")]
    fullData = []
    if len(records) >= 300:
        referenceSequence, diffs = generate_consensus_sequence_from_file(binPath)
        data = []
        sequenceData = []
        clusterSizes = [1]
        for i in range(1, len(records)//iteration+1):
            #if i*iteration == 500: clusterSizes.append(i*iteration)
            clusterSizes.append(i*iteration)
        clusterSizes = clusterSizes[:30] #only go to 300
        if len(clusterSizes) > 100: clusterSizes = clusterSizes[100:]
        for i in clusterSizes:
            levenshteinDistances = []
            sequences = []
            for j in range(30):
                tempRecords = random.sample(records, k=i)
                if i == 1: tempSequence = str(tempRecords[0].seq)
                else:
                    print(generate_consensus_sequence(tempRecords, cutoff_percent=None))
                    tempSequence, _ = generate_consensus_sequence(tempRecords, cutoff_percent=None)
                print('*'*20)
                print('binFile: ' + binPath)
                print('clusterSize: ' + str(i))
                print('iteration: ' + str(j))
                print('distance: ' + str(distance(referenceSequence, tempSequence)))
                print('refSeq: ' + referenceSequence)
                print('temSeq: ' + tempSequence)
                print('*'*20, flush=True)
                levDist = distance(referenceSequence, tempSequence)

                clusterNum = int(re.search(r'seq_bin(\d+).fq', binPath).group(1))
                originalClusterSize = pd.read_csv(outDir + 'starcode_without_chimeras.txt', sep='\t', header=None).iloc[:,1][clusterNum]

                fullData.append([binPath, i, j, referenceSequence, tempSequence, levDist, clusterNum, originalClusterSize])
                levenshteinDistances.append(distance(referenceSequence, tempSequence))
                sequences.append(tempSequence)

            data.append([i] + levenshteinDistances)
            sequenceData.append([i] + sequences)
    fullDf = pd.DataFrame(fullData, columns = ['binPath','clusterSize','iteration','referenceSequence','tempSequence','levenshteinDistance', 'clusterNum', 'originalClusterSize'])
    return fullDf




def cluster_consensus_sequences(outputDir, consensusFile, binFiles):
    binPattern = "seq_bin(\d+)\.fq"
    binPattern = re.compile(binPattern)
    idBinFileDict = {int(binPattern.search(binFile).group(1)):binFile for binFile in binFiles}
    binConsDict = {}
    for record in SeqIO.parse(consensusFile, "fasta"): binConsDict[int(record.id)] = record
    seqs = [str(binConsDict[id].seq) for id in sorted(binConsDict)]
    seqArray = np.array(seqs)
    finalBinFiles = []
    for group in ub.cluster_longread_consensus_sequences(seqs):
        groupIndices = [i for i,x in enumerate(group) if x]
        records = []
        for i in groupIndices:
            records.extend([record for record in SeqIO.parse(idBinFileDict[i], "fastq")])
        superBinFile = outputDir + 'seq_bin_super_' + '_'.join([str(i) for i in groupIndices]) + '.fq'
        with open(superBinFile, "w") as output_handle:
            SeqIO.write(records, output_handle, "fastq")
        finalBinFiles.append(superBinFile)
    return finalBinFiles






def set_command_line_settings():
    parser = argparse.ArgumentParser(description='')
    subparsers = parser.add_subparsers(dest='command', help='CsoDIAq Functions')
    subparsers.add_parser('gui', help='Launches the (optional) GUI application for using longread_umi_python.')
    cons_parser = subparsers.add_parser('cons', help='Identifying Consensus Sequences from UMI-binnable nanopore reads.')
    cons_parser.add_argument('-i', '--input', type=str, required=True, help='Path to folder that only contains input Nanopore read fastq files.')
    cons_parser.add_argument('-o', '--output', type=str, required=True, help='Path for folder output. Folder should not currently exist.')
    cons_parser.add_argument('-a', '--adapters', type=str, required=True, help='A text file with f, F, r, R adapters listed. Defaults to: GAGTGTGGCTCTTCGGAT, ATCTCTACGGTGGTCCTAAATAGT, AATGATACGGCGACCACCGAGATC, and CGACATCGAGGTGCCAAAC, respectively.')
    cons_parser.add_argument('-min', '--minimumReads', type=restricted_int, default=50, help='Minimum number of cluster reads required to generate a consensus sequence. Default is 50.')
    cons_parser.add_argument('-v', '--variants', action="store_true", help='A flag indicating if variants should be deduced from consensus sequences. For example, if consensus sequences 1, 2, and 3 are generated, and sequences 1 and 3 are the same sequence, the variant file will combine them. The variant output would then have 2 sequences.')
    cons_parser.add_argument('-bc', '--benchmarkClusters', action="store_true", help='A flag indicating we want to benchmark the optimal cluster size required to generate an accurate consensus sequence.')
    cons_parser.add_argument('-c', '--consensusAlgorithm', type=str, help='An option between three consensus sequence algorithms. Default is a customized algorithm that relies on pairwise alignment, which can be slow for larger sequences. Options: custom, medaka, mafft')
    #cons_parser.add_argument('-cc', '--customConsensus', action="store_true", help='A flag indicating we want to skip the medaka consensus sequence workflow and only use the custom consensus sequence algorithm. WARNING: this setting can have systematic errors in homopolymeric or long repeat sequences.')
    return parser

def check_for_invalid_input(parser, args):
    if args['command'] == 'cons':
        if not restricted_file_or_directory(args['input']): parser.error('The -i or --input argument must be an existing directory')
        files = os.listdir(args['input'])
        for file in files:
            if not restricted_file_or_directory(file, permittedTypes=['fq', 'fastq']): parser.error('The directory indicated by the -i or --input argument must only contain fastq files (.fq or .fastq)')
        output = restricted_file_or_directory(args['output'], isOutput = True)
        if not output: parser.error('The -o or --output argument must indicate a directory that does not exist yet')
        args['output'] = output
        if not restricted_file_or_directory(args['adapters'], permittedTypes=['txt']): parser.error('The -a or --adapters argument must be an existing file of type text (.txt) format')
        with open(args['adapters'], 'r') as adapterFile: adapters = [adapter.rstrip() for adapter in adapterFile.readlines()]
        if len(adapters) != 4: parser.error('The -a or --adapters argument file must contain 4 adapters.')
        nucleotideCheck = [[characters in ['A','T','G','C'] for characters in adapter] for adapter in adapters]
        if not all(nucleotideCheck): parser.error('The -a or --adapters argument adapters can only contain the nucleotides A,T,G, and C.')
        if args['minimumReads'] < 20: parser.error('The -min or --minimumReads argument must be 20 or higher.')
        if not args['consensusAlgorithm']: args['consensusAlgorithm'] = 'pairwise'
        if args['consensusAlgorithm'] not in ['pairwise','medaka','mafft','lamassemble']: parser.error('The -c or --consensusAlgorithm argument must be `custom`, `medaka`, `mafft`, or `lamassemble`.')
        if args['input'][-1] != '/': args['input'] += '/'
        if args['output'][-1] != '/': args['output'] += '/'
        newOutput = args['output'] + 'delete/'
        args['oldOutput'] = args['output']
        args['output'] = newOutput
        os.mkdir(args['oldOutput'])
        os.mkdir(args['output'])

def restricted_file_or_directory(x, permittedTypes=[], isOutput = False):
    if not len(permittedTypes):
        if isOutput:
            if x[-1] == '/': x = x[:-1]
            name = ''
            if os.path.isdir(x): name += '/ConsSeqUMI'
            name += '-' + time.strftime("%Y%m%d-%H%M%S")
            x += name
            if os.path.isdir(x): return False
            return x

        if not os.path.isdir(x): return False
        else: return True
    if x.split('.')[-1].lower() not in permittedTypes and not os.path.isfile(x): return False
    return True

def restricted_int(x):
    try:
        x = int(x)
    except ValueError:
        raise argparse.ArgumentTypeError("%r not an integer literal" % (x,))
    if x < 1:
        raise argparse.ArgumentTypeError("%r must be an integer greater than 0"%(x,))
    return x


def run_starcode(input, output):
    process = subprocess.Popen(['starcode',
     '-i', input,
     '-o', output,
     '--seq-id',
     #'-s',
     #'-d 5',
     ])
    stdout, stderr = process.communicate()


if __name__ == "__main__":
   main()
