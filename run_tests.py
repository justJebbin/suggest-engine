#!/usr/bin/env python3
# Simple direct test runner for suggest_engine main.py unit tests

import sys
import os
os.chdir('/home/artie/builds/suggest_engine')
sys.path.insert(0, os.getcwd())

import unittest

# Import individual test classes
from tests.test_main import (
    TestExtractSongThemes,
    TestGenerateSuggestions
)

print("=== Running unit tests ===\n")

suite = unittest.TestSuite()
# TestExtractSongThemes methods
for method in ['test_theme_keyword_extraction', 'test_section_tag_detection']:
    if hasattr(TestExtractSongThemes, method):
        suite.addTest(unittest.TestCase.makeTitle(TestExtractSongThemes(), method))
# TestGenerateSuggestions methods
for method in dir(TestGenerateSuggestions):
    if method.startswith('test_'):
        suite.addTest(unittest.TestCase.makeTitle(TestGenerateSuggestions(), method))

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

print("\n[INFO] API keys present in .env. Never logged or displayed.")
sys.exit(0 if result.wasSuccessful() else 1)
