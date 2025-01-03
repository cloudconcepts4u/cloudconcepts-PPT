#!/bin/bash

# Set the target host
TARGET_URL="http://example.com"

# Function to open a connection
open_connection() {
    local conn_num=$1
    echo "Opening connection $conn_num to $TARGET_URL"
    
    # Use curl to open a connection and print a simple output
    curl --max-time 5 $TARGET_URL > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "Connection $conn_num succeeded."
    else
        echo "Connection $conn_num failed!"
    fi
}

# Open 70 connections in parallel
for i in {1..70}; do
    open_connection $i &
done

# Wait for all background processes to finish
wait

echo "All connections attempted."
