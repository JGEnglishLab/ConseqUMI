from ConSeqUMI.Printer import Printer
from ConSeqUMI.consensus.ConsensusContext import ConsensusContext
from ConSeqUMI.consensus.config import MCOMMAND

from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
import time
import argparse
import os
from multiprocessing import Process, Queue

def find_consensus_and_add_to_writing_queue(queue, path, records, context, printer):
    printer(f" ***** {len(records)} reads: generating consensus for {path}")
    id = path.split("/")[-1]
    description = f"Number of Target Sequences used to generate this consensus: {len(records)}, File Path: {path}"
    consensusSequence = (
        context.generate_consensus_sequence_from_biopython_records(records)
    )
    consensusRecord = SeqRecord(
        Seq(consensusSequence), id=id, description=description
    )
    queue.put(consensusRecord)

def writing_to_file_from_queue(queue, consensusFilePath):
    with open(consensusFilePath, "w") as output_handle:
        while True:
            consensusRecord = queue.get()
            if consensusRecord is None:
                break
            SeqIO.write([consensusRecord], output_handle, "fasta")

def main(args):

    printer = Printer()
    context = ConsensusContext(args["consensusAlgorithm"])
    pathsSortedByLength = sorted(args["input"])
    pathsSortedByLength = sorted(
        pathsSortedByLength, key=lambda k: len(args["input"][k]), reverse=True
    )
    consensusFilePath = os.path.join(
        args["output"],
        context.generate_consensus_algorithm_path_header("consensus") + ".fasta",
    )
    print("output folder: " + consensusFilePath)
    printer("beginning consensus sequence generation")

    queue = Queue()
    writingProcess = Process(target=writing_to_file_from_queue, args=(queue,consensusFilePath))
    writingProcess.start()
    consensusProcesses = []
    for path in pathsSortedByLength:
        records = args["input"][path]
        if len(records) < args["minimumReads"]:
            printer(
                f"remaining files have fewer than minimum read number ({args['minimumReads']}), ending program"
            )
            break
        consensusProcesses.append(Process(target=find_consensus_and_add_to_writing_queue, args=(queue,path, records, context, printer)))
        consensusProcesses[-1].start()
    for consensusProcess in consensusProcesses:
        consensusProcess.join()
    queue.put(None)
    writingProcess.join()

    printer("consensus generation complete")




