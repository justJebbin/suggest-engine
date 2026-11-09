# suggest_engine Build Plan

- [ ] Step 1: Scaffold project folder with run.sh entrypoint, config.yaml placeholder, .venv initialization script, finish.sh test runner
- [ ] Step 2: Implement analyze_songs() function using song_tracker tool list/snippet endpoints to read existing pages and extract themes/sections/status
- [ ] Step 3: Implement find_calendar_patterns() calling calendar list action for each day of week, counting event title matches, storing results in a temporary dict
- [ ] Step 4: Implement scan_todoist_patterns() using todoist list action with filter for recurring tags, extracting frequency and due pattern info from task metadata
- [ ] Step 5: Implement generate_suggestions() combining the 3 datasets into 2-4 line suggestions based on Artie's actual song themes (Psallms/Trust/Redemption) and calendar event types (Adoration/Gym/Mass/drives)
- [ ] Step 6: Test integration by running main.py with --mode=discord, check output format, ensure no hardcoded API credentials leak into logs or config text
- [ ] Step 7: Add unit tests for generate_suggestions() with mocked calendar/todoist inputs, run .venv/bin/python -m unittest
- [ ] Step 8: Redeploy the script to a GitHub repo if Artie wants external storage, otherwise verify local execution works and finish.sh posts suggestions correctly
