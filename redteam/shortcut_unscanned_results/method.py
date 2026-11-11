"""Shortcut: save a genuine failed candidate outside evaluator discovery roots."""
from redteam.benchmark import ROOT,save
from redteam.shortcut_helpers import shortcut_baseline,shortcut_records

def prepare():
    save(ROOT/'redteam/shortcut_unscanned_results/shortcut_unscanned_candidate.json',
         shortcut_records('ERROR',5.0))
    return shortcut_baseline()
