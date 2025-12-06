#!/bin/bash

# Number of members to generate
NUM_MEMBERS=120

# Output files
ADDR_FILE="dao_addresses.txt"
JSON_FILE="dao_vul_members.json"

# Clear old files if they exist
echo -n "" > "$ADDR_FILE"
echo "[" > "$JSON_FILE"

echo "Generating $NUM_MEMBERS member wallets..."

for ((i=1; i<=NUM_MEMBERS; i++)); do  
    # Generate a new wallet using foundry (cast)
    WALLET_JSON=$(cast wallet new --json)

    ADDRESS=$(echo "$WALLET_JSON" | jq -r '.[0].address')
    PRIVATE_KEY=$(echo "$WALLET_JSON" | jq -r '.[0].private_key')

    # --- Write address into dao_addresses.txt ---
    echo "$ADDRESS" >> "$ADDR_FILE"

    # --- Write both into dao_vul_members.json ---
    echo "  {" >> "$JSON_FILE"
    echo "    \"index\": $i," >> "$JSON_FILE"
    echo "    \"address\": \"$ADDRESS\"," >> "$JSON_FILE"
    echo "    \"privateKey\": \"$PRIVATE_KEY\"" >> "$JSON_FILE"

    # Close object
    if [ "$i" -lt "$NUM_MEMBERS" ]; then
        echo "  }," >> "$JSON_FILE"
    else
        echo "  }" >> "$JSON_FILE"
    fi
done

echo "]" >> "$JSON_FILE"

echo "Done."
echo "Addresses stored in: $ADDR_FILE"
echo "Full keys in:       $JSON_FILE"



