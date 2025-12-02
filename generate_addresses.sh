#!/bin/bash

# Assume addresses are in a file named addresses.txt, one per line
ADDRESS_FILE="dao_addresses.txt"

echo "[" # Start the Solidity array

# Read addresses into an array
readarray -t addresses < "$ADDRESS_FILE"
NUM_ADDRESSES=${#addresses[@]}

# Loop through the addresses
for ((i=0; i<NUM_ADDRESSES; i++)); do
    ADDRESS="${addresses[$i]}"

    # Print the address
    echo -n "    $ADDRESS"

    # Add a comma and newline if it's not the last address
    if [ "$i" -lt "$((NUM_ADDRESSES - 1))" ]; then
        echo ","
    else
        echo "" # Just a newline for the last one
    fi
done

echo "];" # End the Solidity array
