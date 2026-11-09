# suggest_engine Framework

## Purpose
Periodic pattern analysis across song tracker pages, calendar events, and recurring Todoist tasks to generate proactive musical/creative suggestions for Tenebrae Victae song development.

## How it works
1. **Song Tracker Analysis**: Reads existing Notion pages via song_tracker tool (list_snippets, list pages), extracts lyric themes, section tags ([Verse], [Chorus], etc.), status fields, keywords per page title and notes content. Uses simple text processing (no heavy NLP library) to extract most-frequent section patterns and theme words >3 characters that appear in 2+ song descriptions.

2. **Calendar Pattern Counting**: Uses the calendar tool list action for each day of the week, extracts event titles matching keywords like "Adoration", "Mass", "Gym", "Drive", "Korean", "Pray", then counts occurrences across days to identify weekly rhythms (e.g., Adoration always happens Monday PM, Gym every Tuesday).

3. **Todoist Recurring Detection**: Uses todoist list action with filter like "#songwriting OR recurring OR due_string" to find tasks that repeat, notes task titles with specific due times (morning/evening) or frequency tags, extracts themes from the description field only.

4. **Suggestion Generation** (in main.py):
   - If chord/section patterns are consistent across 3+ songs: suggest a new track using those structures.
   - If calendar shows gaps in creative events during weekends: suggest songwriting block.
   - If lyric snippets exist but no related final songs: propose combining them.
   - Outputs 2-4 bullet points max, formatted as plain text ready for Discord post.

## APIs reference
- `notion_pages` tool (search/read/append/create) — reads existing pages via song_tracker Notion page ID from list_snippets/list results
- `calendar` tool (list free create update) — extracts recurring event types and counts per day
- `todoist` tool (add update complete projects list) — reads tag/frequency/due patterns from tasks

## Build steps
1. Write the core Python script in main.py with functions: analyze_songs(), find_calendar_patterns(), scan_todoist_patterns(), generate_suggestions()
2. Write config.yaml for thresholds (e.g., 3 songs = minimum before suggesting, Sunday 8am cron time).
3. Create run.sh that executes .venv/python main.py --mode=discord
4. Test with dummy data: mock calendar list → ensure no API-key leak in logs.
5. Add unit tests checking that output doesn't include API keys or PII.
6. Write finish.sh that runs test mode, checks output length < 200 lines, then posts to #catholic-songwriting channel via discord_channels tool with a "--- Auto-generated suggestion ---" header.

## Schedule line
Schedule: every sunday 8am
