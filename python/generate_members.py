import json
from eth_account import Account

def generate_members(count=120, output_file="dao_members.json"):
    members = []

    for _ in range(count):
        acct = Account.create()
        members.append({
            "address": acct.address,
            "private_key": acct.key.hex()
        })

    with open(output_file, "w") as f:
        json.dump(members, f, indent=4)

    print(f"Generated {count} members → {output_file}")

if __name__ == "__main__":
    generate_members()
