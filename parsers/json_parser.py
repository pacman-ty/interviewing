import os
from typing import List, Dict

def json_parser(filename: str):
    lines = []

    with open(filename, 'r') as file:
        for line in file:
            if line.strip() == "{":
                continue 
            lines.append(line)

    return helper(lines, {})

# assumption that whitespaces are consistent and a tab is 4 spaces 
def helper(lines: List, json: Dict):
    line = lines.pop(0)

    # base case
    if line.strip().rstrip(",") == "}":
        return json

    key, value = line.split(":", 1)
    key = key.strip().strip('"')
    value = value.strip().rstrip(",").strip('"')

    if value == "{":
        json[key] = helper(lines, {})
    else: 
        json[key] = value
        helper(lines, json)

    return json

for filename in os.listdir("."):
    if filename.endswith(".json"):
        print(f"--- Testing {filename} ---")
        json_data = json_parser(filename)

        for k, v in json_data.items():
            print(f"{k}: {v}")

    print(f"\n")

