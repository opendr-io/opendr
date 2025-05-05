import subprocess
import pandas as pd
import json

# PowerShell command to get hotfixes and convert to JSON
command = [
    "powershell",
    "-Command",
    "Get-HotFix | Select-Object HotFixID, Description, InstalledOn, InstalledBy, PSComputerName | ConvertTo-Json"
]
result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

# JSON  to DataFrame
try:
    hotfix_data = json.loads(result.stdout)
    
    # If only one item is returned, make it a list
    if isinstance(hotfix_data, dict):
        hotfix_data = [hotfix_data]

    dfh = pd.DataFrame(hotfix_data)
    print(dfh.head())
except json.JSONDecodeError as e:
    print("JSON parse error:", e)
    print(result.stdout)

    # If InstalledOn is a dictionary, extract the 'DateTime' field
dfh['InstalledOn'] = dfh['InstalledOn'].apply(lambda x: x.get('DateTime') if isinstance(x, dict) else x)
dfh = dfh.sort_values(by='InstalledOn', ascending=False)

dfh = dfh.rename(columns={
    "InstalledOn": "timestamp",
    "HotFixID": "name",
    "PSComputerName": "hostname",
    "InstalledBy": "username",
    "Description": "description"
})

desired_order = [
    "timestamp",
    "name",
    "hostname",
    "username",
    "description"
]
dfh = dfh[[col for col in desired_order if col in dfh.columns]]
dfh["event"] = "hotfix"

# format output
def format_row_with_keys(row):
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))
lines = dfh.apply(format_row_with_keys, axis=1)

with open("hotfix-inventory.txt", "w", encoding="utf-8") as f:
    for line in lines:
        f.write(line + "\n")
# for debugging, can be removed
print(f"✅ Exported {len(dfh)} rows to hotfix-inventory.txt")