import subprocess
import pandas as pd
from io import StringIO
import re

output_file = "defender_events.txt"
error_file = "errors.txt"

# PowerShell command to fetch Event ID 1116
command = [
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "Get-WinEvent -LogName 'Microsoft-Windows-Windows Defender/Operational' | Where-Object { $_.Id -eq 1116 } | Select-Object TimeCreated, Id, Message | Format-List * "
]

result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
with open(output_file, "w", encoding="utf-8") as f:
    f.write(result.stdout.strip())
if result.stderr.strip():
    with open(error_file, "w", encoding="utf-8") as f:
        f.write(result.stderr.strip())

# debugging, can be removed
if result.returncode == 0:
    print(f"✅ Defender events saved to '{output_file}'.")
else:
    print(f"❌ Error occurred! Check '{error_file}' for details.")

    
# read the raw output
with open("defender_events.txt", "r", encoding="utf-8") as f:
    raw = f.read()

# split entries on 'TimeCreated :' but keep the delimiter
entries = re.split(r'(?=TimeCreated\s+:)', raw.strip())

# read into a dictionary
records = []
for entry in entries:
    record = {}
    lines = entry.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Split on first colon
        if re.match(r'^https?://', line):
            # Put the URL in the correct field
            record["For more information please see the following"] = line.strip()
        elif ':' in line:
            key, value = line.split(':', 1)
            record[key.strip()] = value.strip()
        else:
            # Continuation of previous key's value
            if record:
                last_key = list(record.keys())[-1]
                record[last_key] += ' ' + line.strip()
    records.append(record)

dfwdf = pd.DataFrame(records)
dfwdf = dfwdf.rename(columns={
    "TimeCreated": "timestamp",
    "Id": "event_id",
    "Message": "message"
})

dfwdf["timestamp"] = pd.to_datetime(dfwdf["timestamp"], errors="coerce")
# Drop rows where all fields except 'timestamp' are NaN
dfwdf = dfwdf[~dfwdf.drop(columns=['timestamp']).isna().all(axis=1)]
dfwdf = dfwdf.where(pd.notnull(dfwdf), None)
dfwdf = dfwdf.drop_duplicates()

if "Process Name" in dfwdf.columns:
    idx = dfwdf.columns.get_loc("Process Name")
    # Keep only columns up to and including "Process Name"
    dfwdf = dfwdf.iloc[:, :idx + 1]
dfwdf = dfwdf.drop_duplicates() # remove duplicates

dfwdf = dfwdf.rename(columns={
    "timestamp": "timestamp",
    "event_id": "eventID",
    "message": "description",
    "For more information please see the following": "references",
    "Name": "title",
    "ID": "threat_id",
    "Severity": "severity",
    "Category": "category",
    "Path": "file_path",
    "Detection Origin": "wd-origin",
    "Detection Type": "wd-type",
    "Detection Source": "wd-source",
    "User": "username",
    "Process Name": "executable"
})
dfwdf["event"] = "Windows defender"
desired_order = [
    "timestamp",
    "event",
    "username",
    "title",
    "severity",
    "category",
    "executable",
    "file_path",
    "eventID", 
    "threat_id",
    "wd-origin",
    "wd-type",
    "wd-source",
    "description",
    "references"
]

dfwdf = dfwdf[[col for col in desired_order if col in dfwdf.columns]]


# for debugging
print(f"✅ dataframe created")
print("Number of rows:", len(dfwdf))
print(dfwdf.head())

# output formatted lines
def format_row_with_keys(row):
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))
lines = dfwdf.apply(format_row_with_keys, axis=1)
with open("defender_events.labeled.txt", "w", encoding="utf-8") as f:
    for line in lines:
        f.write(line + "\n")
print(f"✅ Exported {len(dfwdf)} rows to defender_events.labeled.txt")