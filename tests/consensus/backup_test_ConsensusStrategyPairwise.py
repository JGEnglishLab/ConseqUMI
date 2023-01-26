from pytestConsensusFixtures import consensusSequence, readSequences, readSequenceRecords
import pytest
import random
import sys
import os
srcPath = os.getcwd().split("/")[:-1]
srcPath = "/".join(srcPath) + "/src"
sys.path.insert(1, srcPath)

from consensus import ConsensusStrategyPairwise


def test__consensus_strategy_pairwise__initialization():
    pairwise = ConsensusStrategyPairwise.ConsensusStrategyPairwise()
    assert pairwise.aligner.mismatch_score == -1
    assert pairwise.aligner.open_gap_score == -1
    assert pairwise.aligner.extend_gap_score == -0.5

@pytest.fixture
def consensusStrategyPairwise():
    return ConsensusStrategyPairwise.ConsensusStrategyPairwise()

def calculate_average_pairwise_alignment_score_for_tests(consensusSequence):
    baseScore = len(consensusSequence)
    initialErrorScore = baseScore - 1
    allScores = []
    insertionScores = [initialErrorScore-i*0.5 for i in range(5)]
    deletionScores = [initialErrorScore-i*1.5-1 for i in range(5)]
    mutationScores = [initialErrorScore-1 for i in range(5)]
    allScores.extend(insertionScores)
    allScores.extend(deletionScores)
    allScores.extend(mutationScores)
    return sum(allScores) / len(allScores)

def test__consensus_strategy_pairwise__find_average_pairwise_alignment_score(consensusSequence, readSequenceRecords, consensusStrategyPairwise):
    readSequences = [str(readSequenceRecord.seq) for readSequenceRecord in readSequenceRecords]
    averagePairwiseAlignmentScore = calculate_average_pairwise_alignment_score_for_tests(consensusSequence)
    averagePairwiseAlignmentScoreOutput = consensusStrategyPairwise.find_average_pairwise_alignment_score(consensusSequence, readSequences)
    assert averagePairwiseAlignmentScore == averagePairwiseAlignmentScoreOutput

@pytest.fixture
def originalSequence():
    random.seed(0)
    return "".join(random.choices("ATGC", k=20))

@pytest.fixture
def otherNucleotide(): return "R"

@pytest.fixture
def insertionAtFrontSequence(otherNucleotide, originalSequence):
    return otherNucleotide + originalSequence

@pytest.fixture
def insertionAtFrontDifference(otherNucleotide):
    return (0, 0, otherNucleotide)

@pytest.fixture
def insertionAtBackSequence(otherNucleotide, originalSequence):
    return originalSequence + otherNucleotide

@pytest.fixture
def insertionAtBackDifference(otherNucleotide, originalSequence):
    return (len(originalSequence),len(originalSequence),otherNucleotide)

@pytest.fixture
def middleInsertIndex(originalSequence):
    return len(originalSequence) // 2

@pytest.fixture
def insertionAtMiddleSequence(otherNucleotide, originalSequence, middleInsertIndex):
    return originalSequence[:middleInsertIndex] + otherNucleotide + originalSequence[middleInsertIndex:]

@pytest.fixture
def deletionAtFrontDifference():
    return (0,1,"")

@pytest.fixture
def deletionAtMiddleDifference(otherNucleotide, middleInsertIndex):
    return (middleInsertIndex, middleInsertIndex,otherNucleotide)

@pytest.fixture
def insertionAtMiddleDifference(otherNucleotide, middleInsertIndex):
    return (middleInsertIndex, middleInsertIndex,otherNucleotide)

@pytest.fixture
def insertionAtMiddleDifference(otherNucleotide, middleInsertIndex):
    return (middleInsertIndex, middleInsertIndex,otherNucleotide)

def test__consensus_strategy_pairwise__find_all_differences_between_two_sequences__finds_single_insertion_in_front(originalSequence, consensusStrategyPairwise, insertionAtFrontSequence, insertionAtFrontDifference):
    insertionAtFrontDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, insertionAtFrontSequence)
    assert insertionAtFrontDifferenceOutputList[0] == insertionAtFrontDifference

def test__consensus_strategy_pairwise__find_all_differences_between_two_sequences__finds_single_insertion_in_back(originalSequence, consensusStrategyPairwise, insertionAtBackSequence, insertionAtBackDifference):
    insertionAtBackDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, insertionAtBackSequence)
    assert insertionAtBackDifferenceOutputList[0] == insertionAtBackDifference

def test__consensus_strategy_pairwise__find_all_differences_between_two_sequences__finds_single_insertion_in_middle(originalSequence, consensusStrategyPairwise, insertionAtMiddleSequence, insertionAtMiddleDifference):
    insertionAtMiddleDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, insertionAtMiddleSequence)
    assert insertionAtMiddleDifferenceOutputList[0] == insertionAtMiddleDifference

def test_consensus_strategy_pairwise_find_all_differences_between_two_sequences_finds_single_deletion_in_front(originalSequence, consensusStrategyPairwise, insertionAtFrontSequence, ):
    insertionIndex = 10
    originalSequenceEditedForDeletion = otherNucleotide + originalSequence[:insertionIndex] + otherNucleotide + originalSequence[insertionIndex:] + otherNucleotide
    deletionAtFrontSequence = originalSequenceEditedForDeletion[1:]
    deletionAtFrontDifference = (0,1,"")
    deletionAtFrontDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequenceEditedForDeletion, deletionAtFrontSequence)
    assert deletionAtFrontDifferenceOutputList[0] == deletionAtFrontDifference

    deletionAtBackSequence = originalSequenceEditedForDeletion[:-1]
    deletionAtBackDifference = (len(originalSequenceEditedForDeletion)-1,len(originalSequenceEditedForDeletion),"")
    deletionAtBackDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequenceEditedForDeletion, deletionAtBackSequence)
    assert deletionAtBackDifferenceOutputList[0] == deletionAtBackDifference

    deletionInMiddleSequence = originalSequenceEditedForDeletion[:insertionIndex] + originalSequenceEditedForDeletion[insertionIndex+1:]
    deletionInMiddleDifference = (insertionIndex,insertionIndex+1,"")
    deletionInMiddleDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequenceEditedForDeletion, deletionInMiddleSequence)
    assert deletionInMiddleDifferenceOutputList[0] == deletionInMiddleDifference

def test_consensus_strategy_pairwise_find_all_differences_between_two_sequences_finds_single_mutations(originalSequence, otherNucleotide, consensusStrategyPairwise):
    mutationAtFrontSequence = otherNucleotide + originalSequence[1:]
    mutationAtFrontDifference = (0,1,otherNucleotide)
    mutationAtFrontDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, mutationAtFrontSequence)
    assert mutationAtFrontDifferenceOutputList[0] == mutationAtFrontDifference

    mutationAtBackSequence = originalSequence[:-1] + otherNucleotide
    mutationAtBackDifference = (len(originalSequence)-1,len(originalSequence),otherNucleotide)
    mutationAtBackDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, mutationAtBackSequence)
    assert mutationAtBackDifferenceOutputList[0] == mutationAtBackDifference

    mutationIndex = 10
    mutationInMiddleSequence = originalSequence[:mutationIndex-1] + otherNucleotide + originalSequence[mutationIndex:]
    mutationInMiddleDifference = (mutationIndex-1,mutationIndex,otherNucleotide)
    mutationInMiddleDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, mutationInMiddleSequence)
    assert mutationInMiddleDifferenceOutputList[0] == mutationInMiddleDifference

def test_consensus_strategy_find_all_differences_between_two_sequences_finds_insertion_stretches(originalSequence, consensusStrategyPairwise):
    insertionValue = "RRRR"
    insertionAtFrontSequence = insertionValue + originalSequence
    insertionAtFrontDifference = (0,0,insertionValue)
    insertionAtFrontDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, insertionAtFrontSequence)
    assert insertionAtFrontDifferenceOutputList[0] == insertionAtFrontDifference

    insertionAtBackSequence = originalSequence + insertionValue
    insertionAtBackDifference = (len(originalSequence),len(originalSequence),insertionValue)
    insertionAtBackDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, insertionAtBackSequence)
    assert insertionAtBackDifferenceOutputList[0] == insertionAtBackDifference

    insertionIndex = 10
    insertionInMiddleSequence = originalSequence[:insertionIndex] + insertionValue + originalSequence[insertionIndex:]
    insertionInMiddleDifference = (insertionIndex,insertionIndex,insertionValue)
    insertionInMiddleDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, insertionInMiddleSequence)
    assert insertionInMiddleDifferenceOutputList[0] == insertionInMiddleDifference

def test_consensus_strategy_find_all_differences_between_two_sequences_finds_deletion_stretches(originalSequence, consensusStrategyPairwise):
    insertionValue = "RRRR"
    insertionIndex = 10
    originalSequenceEditedForDeletion = insertionValue + originalSequence[:insertionIndex] + insertionValue + originalSequence[insertionIndex + len(insertionValue):] + insertionValue
    deletionAtFrontSequence = originalSequenceEditedForDeletion[len(insertionValue):]
    deletionAtFrontDifference = (0,len(insertionValue),"")
    deletionAtFrontDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequenceEditedForDeletion, deletionAtFrontSequence)
    assert deletionAtFrontDifferenceOutputList[0] == deletionAtFrontDifference

    deletionAtBackSequence = originalSequenceEditedForDeletion[:-len(insertionValue)]
    deletionAtBackDifference = (len(originalSequenceEditedForDeletion)-len(insertionValue),len(originalSequenceEditedForDeletion),"")
    deletionAtBackDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequenceEditedForDeletion, deletionAtBackSequence)
    assert deletionAtBackDifferenceOutputList[0] == deletionAtBackDifference

    deletionInMiddleSequence = originalSequenceEditedForDeletion[:insertionIndex] + originalSequenceEditedForDeletion[insertionIndex+len(insertionValue):]
    deletionInMiddleDifference = (insertionIndex,insertionIndex+len(insertionValue),"")
    deletionInMiddleDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequenceEditedForDeletion, deletionInMiddleSequence)
    assert deletionInMiddleDifferenceOutputList[0] == deletionInMiddleDifference

def test_consensus_strategy_find_all_differences_between_two_sequences_finds_mutation_stretches(originalSequence, consensusStrategyPairwise):
    mutationValue = "RRRR"
    mutationAtFrontSequence = mutationValue + originalSequence[len(mutationValue):]
    mutationAtFrontDifference = (0,len(mutationValue),mutationValue)
    mutationAtFrontDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, mutationAtFrontSequence)
    assert mutationAtFrontDifferenceOutputList[0] == mutationAtFrontDifference
    mutationAtBackSequence = originalSequence[:-len(mutationValue)] + mutationValue
    mutationAtBackDifference = (len(originalSequence)-len(mutationValue),len(originalSequence),mutationValue)
    mutationAtBackDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, mutationAtBackSequence)
    assert mutationAtBackDifferenceOutputList[0] == mutationAtBackDifference
    mutationIndex = 10
    mutationInMiddleSequence = originalSequence[:mutationIndex] + mutationValue + originalSequence[mutationIndex+len(mutationValue):]
    mutationInMiddleDifference = (mutationIndex,mutationIndex+len(mutationValue),mutationValue)
    mutationInMiddleDifferenceOutputList = consensusStrategyPairwise.find_all_differences_between_two_sequences(originalSequence, mutationInMiddleSequence)
    assert mutationInMiddleDifferenceOutputList[0] == mutationInMiddleDifference
