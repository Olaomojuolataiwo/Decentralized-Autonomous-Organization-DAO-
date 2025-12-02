#!/bin/bash

MNEMONIC=$(cat mnemonic.txt)
COUNT=120
OUTPUT_FILE="dao_addresses.txt"

# Clear the output file or create a new one
> $OUTPUT_FILE

for i in $(seq 0 $(($COUNT - 1))); do
    # KEY=$(cast wallet private-key --mnemonic "$MNEMONIC" --mnemonic-index $i)
    ADDRESS=$(cast wallet address --mnemonic "$MNEMONIC" --mnemonic-index $i)
    echo "$ADDRESS" >> $OUTPUT_FILE
done

echo "Generated $COUNT addresses in $OUTPUT_FILE"
