#!/usr/bin/env bash
# suggest_engine test runner and build entrypoint
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Suggest Engine: Virtualenv init if missing ==="
if [ ! -e "$SCRIPT_DIR/.venv/bin/activate" ]; then
    echo "Creating .venv in $SCRIPT_DIR..."
    python3 -m venv "${SCRIPT_DIR}/.venv"
    source "${SCRIPT_DIR}/.venv/bin/activate"
    pip install --quiet -U pip setuptools
    pip install --quiet discord.py requests python-dotenv notion-client google-auth2 google-api-python-client
fi

source "$SCRIPT_DIR/.venv/bin/activate"

echo "=== Checking .env for API keys ==="
if [ ! -e "$SCRIPT_DIR/.env" ]; then
    echo "No .env found — build will not load credentials from disk."
else
    echo ".env exists. Variables loaded into environment only (not logged)."
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs) 2>/dev/null || true
fi

case "${1:-run}" in
	run)
		echo "=== Running main.py with sample data ==="
		cd "$SCRIPT_DIR"
		python3 "$SCRIPT_DIR/main.py" --mode=test 2>&1 | tee output.txt
        
		if [ -f "$SCRIPT_DIR/.env" ]; then
            echo "" >> "$SCRIPT_DIR/output.txt"
            echo "[INFO] API keys present in .env. Never logged or displayed." >> "$SCRIPT_DIR/output.txt"
        fi
		;;
	test)
		echo "=== Running unit tests ==="
		cd "$SCRIPT_DIR"
		
		PATH="$SCRIPT_DIR/.venv/bin:$PATH" python3 -m pytest \
            $SCRIPT_DIR/tests/test_main.py::TestExtractSongThemes::test_theme_keyword_extraction \
            $SCRIPT_DIR/tests/test_main.py::TestExtractSongThemes::test_section_tag_detection \
            $SCRIPT_DIR/tests/test_main.py::TestGenerateSuggestions::test_suggestion_generation_with_section_patterns \
            -v 2>&1 | tee "$SCRIPT_DIR/tests-results.txt"
        
        echo "" >> "$SCRIPT_DIR/tests-results.txt"
        echo "[INFO] API keys present in .env. Never logged or displayed." >> "$SCRIPT_DIR/output.txt"
		;;
	sample)
        echo "=== Creating sample data ==="
        cat > "$SCRIPT_DIR/tests/sample_calendar_data.json" <<'EOF'
[
  {"title": "Adoration @ Saint Mary Roman Catholic Church", "start": "2026-11-09T10:00"},
  {"title": "Gym @ West Pottstown Township YMCA", "start": "2026-11-10T19:00"},
  {"title": "Kyungli Studio Korean Lesson", "start": "2026-11-10T11:30"}
]
EOF
        
        cat > "$SCRIPT_DIR/tests/sample_songs.json" <<'EOF'
[
  {"title": "Leap Like a Deer", "status": "Lyrics Drafting", "lyrics": "[Verse]\nTrust in God\n[Chorus]\nLove and mercy"},
  {"title": "Blind the Night", "status": "Live", "lyrics": "[Bridge]\nSpiritual warfare"}
]
EOF
        echo "Sample test files created."
		;;
*)
	echo "Usage: $0 {run|test|sample}"
	exit 1
	;;
esac
