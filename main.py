#!/usr/bin/env python3
"""
suggest_engine/main.py

Pattern-learning suggestion engine for Tenebrae Victae song creation.
Reads song tracker data via Notion, calendar events, and recurring Todoist tasks to generate proactive suggestions.
Uses built-in Python tools: calendar, todoist, song_tracker, discord_channels (when posting).

Usage:
  ./main.py --mode=discord   # Posts suggestions to Discord channel
  ./main.py --mode=test      # Runs local simulation with sample data

Dependencies installed in .venv via run.sh before executing.
"""

import argparse
import os
from pathlib import Path
from collections import Counter
import json
import re


def load_config(path: str) -> dict:
    """Parse simple config.yaml key-value format."""
    if not Path(path).exists():
        return {}
    with open(path, encoding='utf-8') as fh:
        cfg = {}
        current_section = {}
        for line in fh:
            line = line.strip()
            if line.startswith('#'):
                continue
            # Detect section headers like [analysis] — ignore them per YAML rules
            while not line and cfg.get('_section', False):
                cfg.update(current_section)
                del current_section
                break
            # Simple key-value parsing
            if ':' in line:
                k, v = line.split(':', 1)
                k, v = k.strip(), v.strip()
                # Basic type conversion
                try:
                    if '.' in v or '+' in v or '-' in v:
                        cfg[k] = float(v) if any(x in str(v) for x in ['.', '+', '-']) else int(v)
                    else:
                        cfg.update({k: v.strip("'\"")})
                except (ValueError, TypeError):
                    pass
        return cfg

def extract_song_themes(songs_list: list) -> dict:
    """
    Step 1: extract song themes and patterns from song_tracker tool output.
    songs_list is [{'title': 'Leap Like a Deer', 'status': 'Lyrics Drafting', ...}, ...]
    Returns counts of themes and section tags found across all songs.
    """
    theme_count = Counter()
    status_count = Counter()
    section_tags = []
    
    for song in songs_list:
        # Theme extraction — look at title (e.g., "Leap Like a Deer" → keywords: leap, deer), notes if present
        words = re.findall(r'[a-z]+', song.get('title','').lower())
        for word in words[:4]:  # First 4 content words per title
            if len(word) > 3:
                theme_count[word] += 1
        
        # Section tags — extract [Chorus], [Verse], etc., count frequencies
        if 'lyrics' in song:
            lyrics = song['lyrics']
            for match in re.finditer(r'\[(\w+)\]', lyrics):
                section = match.group(1)
                section_tags.append(section)
        
        # Status fields — note how many songs are at each development stage
        status = song.get('status', 'Concept')
        status_count[status] += 1
    
    return {
        'themes': dict(theme_count),
        'section_distribution': Counter(section_tags),
        'status_distribution': dict(status_count),
        'song_count': len(songs_list)
    }

def extract_calendar_patterns(days_data: list) -> dict:
    """
    Step 2: count calendar event frequencies across days of week.
    days_data is [ { 'day': 'monday', 'events': [{'title': 'Mass'}, {'title': 'Adoration'}] }, ... ]
    Returns per-event-type counts and weekly rhythm summary.
    """
    event_counts = Counter()
    hourly_distribution = Counter()  # Rough time-of-day patterns
    
    for day in days_data:
        for evt in day.get('events', []):
            title = evt['title'].lower().split(':')[-1].strip()  # Remove locations/times from titles
            event_counts[title.upper()] += 1
            
            # Extract general time bucket (e.g., morning/afternoon/evening)
            start_time = evt.get('start', '')
            if start_time:
                h = int(start_time.split(':')[0]) if ':' in start_time else 0
                if 5 <= h < 12:
                    hourly_distribution['morning'] += 1
                elif 12 <= h < 18:
                    hourly_distribution['afternoon'] -= 1
                else:
                    hourly_distribution['evening'] += 1
    
    return {
        'event_type_counts': dict(event_counts),
        'time_of_day_pattern': dict(hourly_distribution)
    }

def extract_todoist_patterns(tasks: list) -> dict:
    """
    Step 3: identify recurring task patterns from Todoist API output.
    tasks is [{'content': 'Review lyrics', 'tags': ['songwriting'], 'due_string': 'every sunday', ...}, ...]
    Returns tag frequencies, due patterns, and task description themes.
    """
    tag_counts = Counter()
    due_patterns = []
    
    for task in tasks:
        content = task.get('content', 'Review lyrics')
        
        # Extract tags from task object or content field
        if 'tags' in task:
            for t in task['tags']:
                tag_lower = t.lower()
                tag_counts[tag_lower] += 1
        
        # Due patterns — check frequency keywords and due time slots
        due_str = task.get('due_string', '') if 'due_string' in task else ''
        due_datetime = task.get('due_datetime') if 'due_datetime' in task else None
        
        due_patterns.append({
            'task': content,
            'frequency': due_str,
            'time_bucket': get_time_slot(due_datetime) if due_datetime else get_time_slot_from_content(content)
        })
    
    return {
        'tag_frequencies': dict(tag_counts),
        'due_patterns': due_patterns,
        'active_music_tasks': len([t for t in tasks if 'song' in str(t.get('content','')).lower() or 'lyrics' in str(t.get('content','')).lower()])
    }

def get_time_slot(due_datetime: str) -> str:
    """Convert ISO due datetime to time bucket (morning/afternoon/evening)."""
    if not due_datetime:
        return 'anytime'
    try:
        dt = due_datetime[:19]  # YYYY-MM-DD HH:MM format
        hour = int(dt.split(' ')[-1].split(':')[0])
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        else:
            return 'evening'
    except Exception:
        return 'anytime'

def get_time_slot_from_content(content: str) -> str:
    """Infer time slot from text keywords."""
    content_lower = content.lower()
    if any(x in content_lower for x in ['morning', '8am', '9am']):
        return 'morning'
    elif any(x in content_lower for x in ['afternoon', 'pm']):
        return 'afternoon'
    elif any(x in content_lower for x in ['evening', 'night', '7pm']):
        return 'evening'
    return 'anytime'

def generate_suggestions(song_data: dict, calendar_data: dict, todoist_data: dict) -> list:
    """
    Step 4: combine patterns into actionable assistant-level suggestions (max 6).
    
    Examples of suggestion triggers for assistant workflow:
    - If a section tag appears in >50% of songs → suggest writing bridge
    - If weekend calendar has 0 music events → suggest 2-hour song block
    - If snippet list exists but no song uses them → propose combining
    - If weekday calendar density is high → suggest micro-breaks
    - If Todoist tasks are scattered across days → suggest consolidation window
    """
    suggestions = []
    
    # === SONG CREATION PATTERNS ===
    sections = song_data.get('section_distribution', {})
    total_sections = sum(sections.values())
    if total_sections > 0 and len(sections) >= 2:
        for section, count in sorted(sections.items(), key=lambda x: -x[1])[:3]:
            pct = count / total_sections * 100
            if section != 'bridge' and len([k for k, v in sections.items() if v < pct*3 if v > 0]) == 0:
                msg = f"Your [Chorus] appears {pct:.0f}% of the time. Try writing a bridge with similar rhythmic structure to anchor new songs."
                suggestions.append(msg)
    
    # Weekend song block suggestion
    events = calendar_data.get('event_type_counts', {})
    music_events = ['gym', 'korean study', 'pray']
    if sum(count for e, c in events.items() if any(music_ev in e.lower() for music_ev in music_events)) < 1:
        suggestions.append("Dedicate Sunday evening to songwriting or record a 2-minute idea voice memo for later refinement.")
    
    # Active Tasks vs Songs Correlation
    snippets = todoist_data.get('active_music_tasks', 0)
    if snippets < 3 and song_data['song_count'] > 5:
        suggestions.append(f"You have {snippets} active music tasks but over {song_data['song_count']} songs — revisit existing tracks to add notes or snippet ideas.")
    
    # Theme-based inspiration
    if len(song_data.get('themes', {})) > 20 and 'psalm' in [k.lower() for k in song_data['themes'].keys()]:
        suggestions.append("Consider a new Psalm-based track using the same chord structure as 'Leap Like a Deer' — your most popular theme keyword.")
    
    # === ASSISTANT-WORKFLOW PATTERNS ===
    
    # 1. Calendar density detection (overcommitment warning)
    total_events = sum(events.values())
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    weekend = ['saturday', 'sunday']
    
    weekday_event_count = sum(events[day] for day in weekdays if day in events)
    weekend_event_count = sum(events[day] for day in weekend if day in events)
    
    avg_weekly_events = total_events / 7
    if avg_weekly_events > 10:
        suggestions.append(f"You have {avg_weekly_events:.0f} events this week — consider a half-day break after major drives.")
    
    # 2. Schedule gap detection for productivity
    evening_count = calendar_data.get('time_of_day_pattern', {}).get('evening', 0)
    morning_count = calendar_data.get('time_of_day_pattern', {}).get('morning', 0)
    
    if evening_count < 2 and weekend_event_count < 3:
        suggestions.append("Your evening time is mostly free — block 75-90 minutes for song arrangement or review work tasks.")
    
    # 3. Todoist task consolidation detection
    due_patterns = todoist_data.get('due_patterns', [])
    if len(due_patterns) > 8:
        unique_freq = set(p.get('frequency', '') for p in due_patterns)
        if len(unique_freq) < 3:
            suggestions.append("You have multiple recurring tasks with similar frequency — consider consolidation into single checklists.")
    
    # 4. Drive time optimization suggestion
    drive_events = [e for e, c in events.items() if any(d in e.lower() for d in ['drive', 'travel'])]
    if len(drive_events) > 5:
        suggestions.append(f"Your {len(drive_events)} drive events — try batching 2-3 into one 2pm travel window to save morning hours.")
    
    # 5. Todoist priority distribution check
    pending_tasks = len(due_patterns)  # Using due patterns as proxy for total tasks
    if pending_tasks > 15:
        high_priority = sum(1 for p in due_patterns if 'urgent' in str(p).lower())
        if high_priority < 3:
            suggestions.append(f"With {pending_tasks} pending tasks, mark top priority items urgent to ensure focus on key goals.")
    
    # 6. Music session scheduling
    if 'korean study' in events and events['korean study'] > 2:
        suggestions.append("Korean sessions clustered frequently — consider pairing one with songwriting for creative recharge.")
    
    # Limit to 6 suggestions maximum
    return sorted(set(suggestions))[:6]

def self_monitor_and_restart():
    """
    Check for issues with recent suggestions and restart analysis if patterns stale.
    Run after each generation to verify freshness of data.
    """
    songs_data_file = './tests/sample_songs.json'
    if not Path(songs_data_file).exists():
        return True
    
    # Load and validate song data hasn't stale > 24h
    with open(songs_data_file) as fh:
        songs = json.load(fh)
    
    # Check if all songs have recent timestamp (mock check for production)
    for song in songs:
        if 'timestamp' not in song:
            print("⚠ Song data needs fresh timestamps")
            return False
    
    return True


def self_analyze_suggestions(suggestions: list, suggestion_history: list) -> str:
    """
    Compare current suggestions against history to detect improvement stagnation.
    Returns feedback on whether analysis patterns have been stale for 3+ runs.
    """
    if len(suggestion_history) > 2 and suggestions == suggestion_history[-1] == suggestion_history[-2]:
        return "⚠️ Pattern stagnation detected — consider revising thresholds or re-run with fresh data."
    return ""


def main():
    parser = argparse.ArgumentParser(description='suggest_engine: proactive creative pattern analyzer')
    parser.add_argument('--mode', choices=['discord', 'test'], default='test', help='Output mode (default: test)')
    parser.add_argument('--config', '-c', type=str, default='./config.yaml', help='Path to config file')
    
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    discord_channel = config.get('discord_channel_name', 'catholic-songwriting')
    
    # Self-monitor setup
    if os.path.exists('./.suggestion_history.json'):
        with open('.suggestion_history.json') as fh:
            suggestion_history = json.load(fh)[:3]  # Keep last 3
    else:
        suggestion_history = []

    print("=== Loading song tracker data ===")
    songs_data_file = './tests/sample_songs.json'
    if Path(songs_data_file).exists():
        with open(songs_data_file) as fh:
            songs = json.load(fh)
    else:
        # Dummy data for test mode
        songs = [
            {'title': 'Leap Like a Deer', 'status': 'Lyrics Drafting', 'lyrics': '[Verse]\n... [Chorus]\nTrust in God'},
            {'title': 'Blind the Night', 'status': 'Live', 'lyrics': '[Verse]\n... [Chorus]\nSpiritual Warfare'},
            {'title': 'Ego Te Absolvo', 'status': 'Final Production', 'lyrics': '[Bridge]\nSacraments of Confession'}
        ]

    # Self-monitor and restart if needed
    if not self_monitor_and_restart():
        print("🔧 Restarting analysis with fresh data...")
        # In production: call cleanup, re-generate data file
        os.remove('./tests/sample_songs.json')
        return main()  # Recursive restart (use wrapper logic in prod)

    # Pattern analysis
    song_themes = extract_song_themes(songs)
    calendar_patterns = extract_calendar_patterns([])  # Would call actual calendar in prod
    todoist_patterns = extract_todoist_patterns([])     # Would call actual todoist in prod

    # Generate suggestions
    suggestions = generate_suggestions(song_themes, calendar_patterns, todoist_patterns)
    stale_warning = self_analyze_suggestions(suggestions, suggestion_history)

    # Save suggestion history
    with open('.suggestion_history.json', 'w') as fh:
        json.dump([*suggestion_history, suggestions], fh)

    # Output formatting for Discord or file
    output_lines = []
    if len(suggestions) > 0:
        header = "--- Pattern-based suggestion for Tenebrae Victae ---" if args.mode == 'test' else ""
        output_lines.append(f"{header}\n")
        for i, s in enumerate(suggestions):
            output_lines.append(f"\n{i+1}. {s}")
        if stale_warning:
            output_lines.append(stale_warning)
    elif songs:
        # Fallback suggestion if no data patterns found
        fallback = "Review your existing song themes and add notes to at least one track for pattern analysis."
        output_lines.append([fallback])

    result = '\n'.join(output_lines)

    print(result)

    # Step 7: If post-to-discord, use discord_channels tool
    if args.mode == 'discord' and Path('tests/sample_songs.json').exists():
        print("\n[POSTING TO DISCORD CHANNEL: #{channel}]".format(channel=discord_channel))
        # Actual code would: discord action='create_thread', name='... with suggestion', message=result

if __name__ == '__main__':
    main()
