#!/bin/bash

echo "Starting Ralph Loop..."

while true; do
  echo "==================================="
  echo "🚀 Starting new Claude Code loop..."
  echo "==================================="
  
  # Run Claude Code with the PROMPT.md
  winpty claude.cmd -p PROMPT.md --dangerously-skip-permissions --verbose
  
  echo "✅ Loop completed. Waiting 3 seconds before next loop..."
  sleep 3
done
