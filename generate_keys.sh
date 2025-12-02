#!/bin/bash

MNEMONIC=$(cat mnemonic.txt)
COUNT=120
OUTPUT_FILE="dao_members.txt"

# Clear the output file if it exists, or create a new one
> $OUTPUT_FILE

for i in $(seq 0 $(($COUNT - 1))); do
    # Use cast wallet private-key to get the key and append it to the file
    cast wallet private-key --mnemonic "$MNEMONIC" --mnemonic-index $i >> $OUTPUT_FILE
done

echo "Generated $COUNT private keys in $OUTPUT_FILE"
