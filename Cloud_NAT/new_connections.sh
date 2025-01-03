#!/bin/bash

# Set the target host
TARGET_URL="http://example.com"
MAX_RETRIES=5  # Maximum number of retries for each connection
RETRY_DELAY=2  # Delay between retries in seconds

# Function to open a connection with retry logic
open_connection() {
    local conn_num=$1
    local retries=0
    local success=false

    echo "Opening connection $conn_num to $TARGET_URL"
    
    while [ $retries -lt $MAX_RETRIES ]; do
        # Use curl to open a connection and print a simple output
        curl --max-time 5 $TARGET_URL > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            echo "Connection $conn_num succeeded."
            success=true
            break
        else
            retries=$((retries + 1))
            echo "Connection $conn_num failed. Retry attempt $retries of $MAX_RETRIES..."
            sleep $RETRY_DELAY
        fi
    done
    
    if [ "$success" = false ]; then
        echo "Connection $conn_num failed after $MAX_RETRIES retries."
    fi
}

# Open 70 connections in parallel
for i in {1..130}; do
    open_connection $i &
done

# Wait for all background processes to finish
wait

echo "All connections attempted."
