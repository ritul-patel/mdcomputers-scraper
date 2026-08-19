#!/usr/bin/env bash
#
# company_founding_years.sh
#
# Downloads the S&P 500 constituents CSV and prints:
#   Company Name, Location, Founding Year
# sorted by founding year (ascending).
#
# Usage:
#   ./company_founding_years.sh
#   ./company_founding_years.sh > companies_by_year.csv
#
# The source CSV columns are:
#   Symbol,Security,GICS Sector,GICS Sub-Industry,Headquarters Location,Date added,CIK,Founded
#
# The "Founded" column is sometimes messy, e.g.:
#   "2013 (1888)"
#   "2020 (1915, United Technologies spinoff)"
#   "1975/1977 (1997)"
# We take the FIRST 4-digit year we find in that field as the sort key,
# but still print the original "Founded" text so no information is lost.
#
# CSV parsing (handling quoted fields with embedded commas) is done with
# a small inline Python3 helper, since that is far more reliable than
# splitting on commas with awk/cut for real-world CSV data.

set -euo pipefail

CSV_URL="https://raw.githubusercontent.com/datasets/s-and-p-500-companies/refs/heads/main/data/constituents.csv"
TMP_CSV="$(mktemp)"

trap 'rm -f "$TMP_CSV"' EXIT

echo "Downloading CSV..." >&2
curl -fsSL "$CSV_URL" -o "$TMP_CSV"

python3 - "$TMP_CSV" <<'PYEOF'
import csv
import re
import sys

path = sys.argv[1]

rows = []
with open(path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get("Security", "").strip()
        location = row.get("Headquarters Location", "").strip()
        founded_raw = row.get("Founded", "").strip()

        match = re.search(r"\d{4}", founded_raw)
        sort_year = int(match.group()) if match else 0

        rows.append((sort_year, name, location, founded_raw))

rows.sort(key=lambda r: r[0])

writer = csv.writer(sys.stdout)
writer.writerow(["Company Name", "Location", "Founding Year"])
for _, name, location, founded_raw in rows:
    writer.writerow([name, location, founded_raw])
PYEOF
