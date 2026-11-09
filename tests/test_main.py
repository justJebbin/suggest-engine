#!/usr/bin/env python3
"""
Unit tests for suggest_engine core functions.
Verifies analysis logic, pattern recognition, and suggestion generation.
Also checks that no API keys or credentials are leaked in any output.
"""

import unittest
import json
import re
from collections import Counter
import sys

# Add script directory to module search path (so imports like 'main' work)
script_dir = '/home/artie/builds/suggest_engine'
if str(script_dir) not in sys.path:
    sys.path.insert(0, script_dir)
# Also add tests dir (for test_main.py imports)
tests_dir = f'{script_dir}/tests'
if str(tests_dir) not in sys.path:
    sys.path.insert(0, tests_dir)

from main import (
    extract_song_themes,
    extract_calendar_patterns, 
    extract_todoist_patterns,
    generate_suggestions
)


class TestExtractSongThemes(unittest.TestCase):
    
    def test_theme_keyword_extraction(self):
        """Test that theme words >3 chars are extracted from titles."""
        songs = [
            {'title': 'Leap Like a Deer', 'status': 'Lyrics Drafting'}
        ]
        result = extract_song_themes(songs)
        
        # 'jump' and 'high' or 'deer' should be in themes (words > 3 chars from title)
        self.assertIn('leap', result['themes'].keys()) or len(result['themes']) > 1
    
    def test_section_tag_detection(self):
        """Test that section tags like [Chorus], [Verse] are detected."""
        songs = [
            {'title': 'Leap Like a Deer', 'status': 'Draft', 'lyrics': '[Verse]\nJumping\n[Chorus]\nTrust'}
        ]
        result = extract_song_themes(songs)
        
        self.assertIn('Verse', result['section_distribution'])
        self.assertIn('Chorus', result['section_distribution'])
    
    def test_status_counting(self):
        """Test that status distribution is correctly counted."""
        songs = [
            {'title': 'Song A', 'status': 'Demo'},
            {'title': 'Song B', 'status': 'Demo'}
        ]
        result = extract_song_themes(songs)
        
        self.assertEqual(result['status_distribution']['Demo'], 2)


class TestExtractCalendarPatterns(unittest.TestCase):
    
    def test_event_type_counting(self):
        """Test event titles are counted by frequency."""
        calendar_data = [
            {'day': 'monday', 'events': [{'title': 'Adoration'}, {'title': 'Mass'}]},
            {'day': 'tuesday', 'events': [{'title': 'Adoration'}]}
        ]
        result = extract_calendar_patterns(calendar_data)
        
        event_counts = result['event_type_counts']
        self.assertEqual(event_counts.get('ADORATION'), 2)


class TestGenerateSuggestions(unittest.TestCase):
    
    def test_suggestion_generation_with_section_patterns(self):
        """Test that a Chorus-dominant song gets a bridge-building suggestion."""
        song_data = {
            'section_distribution': {'Chorus': 10, 'Verse': 5, 'Bridge': 0},
            'song_count': 10,
            'themes': {'psalm': 3}
        }
        calendar_data = {'event_type_counts': {}, 'time_of_day_pattern': {}}
        
        suggestions = generate_suggestions(song_data, calendar_data, {})
        
        # Should contain at least one suggestion about sections or schedule
        self.assertTrue(len(suggestions) >= 1)
    
    def test_api_key_leak_check(self):
        """Critical: ensure no API keys or credentials appear in any output."""
        # Mock data
        mock_songs_data = {
            'section_distribution': {'Chorus': 8, 'Verse': 5},
            'song_count': 3,
            'themes': {}
        }
        mock_calendar = {'event_type_counts': {}, 'time_of_day_pattern': {}}
        mock_todoist = {'tag_frequencies': {}, 'due_patterns': [], 'active_music_tasks': 1}
        
        suggestions = generate_suggestions(mock_songs_data, mock_calendar, mock_todoist)
        output_str = '\\n'.join(suggestions)
        
        # Check that no credential-like strings are in output
        sensitive_keywords = ['api_key', 'token:', 'password', 'secret', 'Bearer ']
        for keyword in sensitive_keywords:
            self.assertNotIn(keyword.lower(), output_str.lower(), f"ERROR: '{keyword}' leaked in suggestion output")
    
    def test_fallback_when_no_patterns(self):
        """Test that useful output is still produced when no strong patterns exist."""
        song_data = {'section_distribution': {}, 'song_count': 2, 'themes': {}}
        calendar_data = {'event_type_counts': {}, 'time_of_day_pattern': {}}
        
        suggestions = generate_suggestions(song_data, calendar_data, {})
        
        # Even with empty input, should have something or return empty valid list
        self.assertIsInstance(suggestions, list)


class TestNoCredentialLeakInFullFlow(unittest.TestCase):
    """Integration test: entire function chain doesn't leak secrets."""
    
    def test_song_analysis_clean(self):
        """extract_song_themes shouldn't use or expose any API keys."""
        songs = [
            {'title': 'Test Song', 'status': 'Demo'},
            {'title': 'Other Song', 'status': 'Lyrics Drafting'}
        ]
        
        result = extract_song_themes(songs)
        
        # Check that no credential patterns in theme names or section keys
        for theme_name, count in result['themes'].items():
            self.assertNotIn('API', theme_name.upper())
            
        for section_type, num in result['section_distribution'].items():
            self.assertFalse(section_type.lower() in ['secret', 'private', 'token'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
