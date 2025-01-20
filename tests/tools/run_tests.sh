#!/bin/bash

# Set up Python path
export PYTHONPATH=/Users/jkneen/Documents/Cline/MCP/claude-engineer

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Change to the script's directory
cd "$(dirname "$0")"

echo "Running tool tests..."
echo "===================="

# Run individual tool tests
for test_file in test_error_handler.py test_file_reader.py; do
    if [ -f "$test_file" ]; then
        echo -e "\nRunning ${GREEN}$test_file${NC}"
        python3 -m pytest "$test_file" -v
        if [ $? -ne 0 ]; then
            echo -e "${RED}Tests failed for $test_file${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Test file not found: $test_file${NC}"
        exit 1
    fi
done

echo -e "\n${GREEN}All tests completed successfully${NC}"