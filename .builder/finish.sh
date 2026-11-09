#!/usr/bin/env bash
# finish.sh — suggest_engine build verification (Step 8)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
OUTPUT_FILE="$SCRIPT_DIR/../output.md"

echo "=== verify step 1: create output file path ==="
touch "$OUTPUT_FILE" || {
  echo "FAIL: Cannot write to $OUTPUT_FILE" >&2  
  exit 1
}

echo "=== Step 2: create dummy calendar data for testing ==="
mkdir -p "$SCRIPT_DIR/tests"
cat > "$SCRIPT_DIR/tests/sample_calendar_data.json" <<EOF
{"monday":[{"title":"Adoration","description":"6:00 PM"},{"title":"Korean study","description":"8:00 AM"}]}
EOF

# SCRIPT_DIR is .builder — use parent for main.py and tests/
ENGINE_DIR="$(cd "$SCRIPT_DIR/../" && pwd)"

echo "=== Step 3: run main.py with test mode ==="
export PYTHONPATH="$ENGINE_DIR:$PYTHONPATH"
$ENGINE_DIR/.venv/bin/python3 "$ENGINE_DIR/main.py" --mode=test > "$ENGINE_DIR/test_output.txt" || {
  echo "FAIL: main.py did not complete successfully" >&2
  cat "$SCRIPT_DIR/test_output.txt" >&2
  exit 1
}

echo "=== Step 4: check output length and format ==="
LINES=$(wc -l < "$SCRIPT_DIR/test_output.txt")
if [ "$LINES" -gt 20 ]; then
  echo "FAIL: Output too long ($LINES lines) — should be max 10 lines for short suggestions" >&2
  exit 1
fi
if ! grep -q "Song idea\|snippet opportunity\|Inspiration\|Dedicate" "$SCRIPT_DIR/../test_output.txt"; then
  echo "FAIL: Output lacks expected suggestion formats" >&2  
  cat "$SCRIPT_DIR/test_output.txt" >&2
  exit 1
fi

echo "=== Step 5: verify no API keys or credentials leaked ==="
if grep -qiE "(api_key|secret|token|password)" "$SCRIPT_DIR/test_output.txt"; then
  echo "FAIL: Credentials or API keys found in output" >&2
  exit 1
fi

echo "=== Step 6: run unit tests for main.py ==="
export PYTHONPATH="$ENGINE_DIR:$PYTHONPATH"
$ENGINE_DIR/.venv/bin/python3 -m pytest \
  "$ENGINE_DIR/tests/test_main.py::TestExtractSongThemes::test_theme_keyword_extraction" \
  "$ENGINE_DIR/tests/test_main.py::TestExtractSongThemes::test_section_tag_detection" \
  "$ENGINE_DIR/tests/test_main.py::TestGenerateSuggestions::test_suggestion_generation_with_section_patterns" \
  -v

echo "=== Step 7: verify finish.sh can run again cleanly ==="
# Use absolute path for run.sh in suggest_engine root and ensure venv/bin is in PATH
cd "$ENGINE_DIR"
PATH="$ENGINE_DIR/.venv/bin:$PATH" bash "$ENGINE_DIR/run.sh" test

echo "=== BUILD COMPLETE ==="
echo "Test output written to $SCRIPT_DIR/test_output.txt (length=$LINES)"
echo "Suggestions sample:"
cat "$SCRIPT_DIR/../test_output.txt" | head -6
echo ""
echo "Deploy: command usage — run '$SCRIPT_DIR/run.sh' in .venv/python environment."
