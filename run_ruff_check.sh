#!/bin/bash

# Change to the project directory
cd "$(dirname "$0")"

# Parse command line arguments
FIX=false
UNSAFE=false

# Process command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --fix)
      FIX=true
      shift
      ;;
    --unsafe-fixes)
      UNSAFE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--fix] [--unsafe-fixes]"
      exit 1
      ;;
  esac
done

# Run ruff check using uv
if [ "$FIX" = true ] && [ "$UNSAFE" = true ]; then
  echo "Running ruff check with fixes (including unsafe fixes)..."
  uv run ruff check --fix --unsafe-fixes .
elif [ "$FIX" = true ]; then
  echo "Running ruff check with fixes..."
  uv run ruff check --fix .
else
  echo "Running ruff check..."
  uv run ruff check .
fi

# Exit with the same status code as ruff
exit $?
