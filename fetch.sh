#!/bin/sh
# Refresh the source data, then run: python3 build.py
# The two SFUSD sheets and the GreatSchools listings change over time; charter-info.json is hand-maintained.
set -e
cd "$(dirname "$0")"
curl -sfL -o data/main-round.csv "https://docs.google.com/spreadsheets/d/16mtV4GchcWsl6xs6oUrVy6edmNRXzBU6lgbkLlwxiHI/export?format=csv&gid=0"
curl -sfL -o data/waitlist.csv "https://docs.google.com/spreadsheets/d/1hatg8laSrgwwH8Zf1z4RPCNF0ICIX7rEXv3aq5f3FDo/export?format=csv&gid=1104076014"
curl -sfL -o geo/neighborhoods.geojson "https://data.sfgov.org/resource/j2bu-swwd.geojson"
python3 - <<'PY'
import json, re, time, urllib.request
def listing(kind):
    out, page = {}, 1
    while True:
        url = f"https://www.greatschools.org/california/san-francisco/schools/?page={page}&st%5B%5D={kind}"
        html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"})).read().decode()
        data = json.loads(re.search(r"gon\.search=(\{.*?\});gon\.", html, re.S).group(1))
        for s in data["schools"]:
            out[s["id"]] = s
        if page >= data["totalPages"]:
            return list(out.values())
        page += 1
        time.sleep(1)
json.dump(listing("public"), open("geo/greatschools-public.json", "w"))
json.dump(listing("charter"), open("geo/greatschools-charter.json", "w"))
PY
echo "Data refreshed. Now run: python3 build.py"
