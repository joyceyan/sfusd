"""Build index.html (GitHub Pages) and artifact.html (Claude artifact) from template.html and the data files.

Run from the repo root: python3 build.py
"""
import csv, json, math, re, collections

a = list(csv.reader(open('data/main-round.csv')))[2:]
braw = list(csv.reader(open('data/waitlist.csv')))
upd = braw[1][2]
b = braw[3:]
sped = lambda p: 'SDC' in p
B = {r[0]: r for r in b if r[0]}
n = lambda s: int(s.replace(',', '')) if re.fullmatch(r'[\d,]+', s) else None
p = lambda s: int(s[:-1]) if re.fullmatch(r'\d+%', s) else None

rows = []
esaa = collections.Counter()
for r in a:
    if not r[1] or sped(r[6]):
        continue
    w = B.get(r[1])
    rows.append([r[3], r[4], r[5], r[6], r[0], n(r[7]), n(r[8]), p(r[9]), n(r[10]), p(r[11]), n(r[12]), n(r[15]),
                 n(r[17]), p(r[21]), n(r[32]), p(r[36])] + ([n(w[6]), n(w[7]), n(w[8]), n(w[9])] if w else [None] * 4) + [n(r[13]), n(r[18]), n(r[20]), n(r[33]), n(r[35]), p(r[19]), p(r[34])])
    esaa[r[3]] += n(r[17])
schools = sorted({r[0] for r in rows})
aa = {s for s in schools if esaa[s] > 0}
stray = sorted({(r[0], r[2]) for r in rows if r[12] and r[2] != 'GE'})
print('attendance-area schools', len(aa), '| ESAA requests on rows classed city-wide:', stray)

# --- projection
gs = json.load(open('geo/greatschools-public.json'))
nb = json.load(open('geo/neighborhoods.geojson'))
rings = []
for f in nb['features']:
    for poly in f['geometry']['coordinates']:
        ring = poly[0]
        if min(x for x, y in ring) > -122.56:
            rings.append((f['properties']['nhood'], ring))
lon0 = min(x for _, r in rings for x, y in r); lon1 = max(x for _, r in rings for x, y in r)
lat0 = min(y for _, r in rings for x, y in r); lat1 = max(y for _, r in rings for x, y in r)
C = math.cos(math.radians(37.77))
K = 1000 / ((lon1 - lon0) * C)
proj = lambda lon, lat: ((lon - lon0) * C * K, (lat1 - lat) * K)
H = round((lat1 - lat0) * K)

def dp(pts, tol):
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        (x1, y1), (x2, y2) = pts[i], pts[j]
        dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-9
        best, bi = 0, None
        for k in range(i + 1, j):
            d = abs(dy * (pts[k][0] - x1) - dx * (pts[k][1] - y1)) / L if L > 1e-6 else math.hypot(pts[k][0] - x1, pts[k][1] - y1)
            if d > best: best, bi = d, k
        if bi is not None and best > tol:
            keep[bi] = True; stack += [(i, bi), (bi, j)]
    return [q for q, k in zip(pts, keep) if k]

geo = collections.OrderedDict()
for name, ring in rings:
    pts = [proj(x, y) for x, y in ring]
    mid = len(pts) // 2
    s = dp(pts[:mid + 1], 1.2) + dp(pts[mid:], 1.2)[1:]
    area = abs(sum(s[i][0] * s[i + 1][1] - s[i + 1][0] * s[i][1] for i in range(len(s) - 1))) / 2
    if len(s) < 4 or area < 30:
        continue
    d = 'M' + 'L'.join(f'{round(x)},{round(y)}' for x, y in s[:-1]) + 'Z'
    xs = [x for x, y in s]; ys = [y for x, y in s]
    g = geo.setdefault(name, {'d': '', 'area': 0, 'c': None})
    g['d'] += d
    if area > g['area']:
        g['area'] = area; g['c'] = (round((min(xs) + max(xs)) / 2), round((min(ys) + max(ys)) / 2))
GEO = [[k, v['d'], v['c'][0], v['c'][1]] for k, v in geo.items()]

# --- match schools to GreatSchools
stop = {'es', 'ms', 'hs', 'k', '8', 'ees', 'school', 'elementary', 'middle', 'high', 'the', 'of', 'at', 'and', 'jr', 'dr',
        'academy', 'prek', 'tk', '5', '6', '12', '9', 'sf', 'san', 'francisco', 'early', 'education', 'alternative',
        'children', 'center', 's'}
tok = lambda s: {t for t in re.findall(r'[a-z0-9]+', s.lower().replace("'", ''))} - stop
OVERRIDE = {
    'Argonne EES': None, 'Serra (Junipero) Annex EES': None, 'Rodriguez (Zaida T) EES': None, 'Mission Bay ES': None,
    'Francisco MS': 'Francisco Middle School', 'Mission Education Center ES': 'Mission Education Center',
    'Visitacion Valley MS': 'Visitacion Valley Middle School', 'Visitacion Valley ES': 'Visitacion Valley Elementary School',
    'Mission HS': 'Mission High School', 'Marshall ES': 'Marshall Elementary School', 'Presidio MS': 'Presidio Middle School',
    'SF Community K-8': 'San Francisco Community Alternative School', 'Washington (George) HS': 'Washington (George) High School',
    'SF Public Montessori ES': 'San Francisco Public Montessori School',
}
MANUAL_LL = {  # early education sites absent from GreatSchools; Census geocoder, Appleton Ave approximate
    'Argonne EES': (-122.474545, 37.773929), 'Rodriguez (Zaida T) EES': (-122.418282, 37.749821),
    'Serra (Junipero) Annex EES': (-122.4228, 37.7386), 'Mission Bay ES': (-122.395224, 37.769858),
}
SCH = {}
for s in schools:
    if s in OVERRIDE:
        g = next((x for x in gs if OVERRIDE[s] and x['name'].startswith(OVERRIDE[s])), None)
        assert g or OVERRIDE[s] is None, s
    else:
        t = tok(s)
        g = max(gs, key=lambda x: len(t & tok(x['name'])) / len(t))
        assert len(t & tok(g['name'])) / len(t) >= 0.66, s
    lon, lat = (g['lon'], g['lat']) if g else MANUAL_LL[s]
    x, y = proj(lon, lat)
    level = 'Y' if s.endswith(' EES') else 'M' if s.endswith(' MS') else 'H' if s.endswith(' HS') else 'E'
    SCH[s] = [round(x, 1), round(y, 1), g['rating'] if g else None, g['links']['profile'] if g else None, 1 if s in aa else 0, level]
print('schools', len(SCH), 'rated', sum(1 for v in SCH.values() if v[2]), 'no GS profile', [k for k, v in SCH.items() if not v[3]])
print('unrated with profile', [k for k, v in SCH.items() if v[3] and not v[2]])
print('bounds', min(v[0] for v in SCH.values()), max(v[0] for v in SCH.values()), min(v[1] for v in SCH.values()), max(v[1] for v in SCH.values()), 'H', H)

import os
info = {i['name']: i for i in json.load(open('geo/charter-info.json'))} if os.path.exists('geo/charter-info.json') else {}
CHD = {}
for s in json.load(open('geo/greatschools-charter.json')):
    if 'Five Keys' in s['name'] or 'Mary L. Booker' in s['name']:  # adult/in-custody programs; Booker closed in 2020 per CDE
        continue
    x, y = proj(s['lon'], s['lat'])
    low = s['gradeLevels'].split('-')[0]
    ad = s['address']
    CHD[s['name']] = dict(x=round(x, 1), y=round(y, 1), r=s.get('rating'), path=s['links']['profile'], grades=s['gradeLevels'],
        lvl='H' if low == '9' else 'M' if low in ('5', '6') else 'E', enroll=s.get('enrollment'), spt=s.get('studentsPerTeacher'),
        low=s.get('percentLowIncome'), parent=s.get('parentRating'), reviews=s.get('numReviews'),
        addr=f"{ad['street1']}, {ad['city']} {ad['zip']}", sub=s.get('subratings') or {}, info=info.get(s['name']))
print('charters', len(CHD), 'with info', sum(1 for c in CHD.values() if c['info']), 'info unmatched', [k for k in info if k not in CHD])
J = lambda o: json.dumps(o, separators=(',', ':'), ensure_ascii=False)
t = open('template.html').read()
for k, v in (('__DATA__', J(rows)), ('__SCH__', J(SCH)), ('__CH__', J(CHD)), ('__GEO__', J(GEO)), ('__H__', str(H)), ('__UPDATED__', upd)):
    assert k in t, k
    t = t.replace(k, v)
open('artifact.html', 'w').write(t)   # fragment for a Claude artifact, which adds its own document skeleton

# Standalone page for GitHub Pages: same content inside a full document.
head, body = t.split('\n<div class="wrap" id="page">', 1)
open('index.html', 'w').write(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="Main-round and waitlist odds for every SFUSD school, program and grade, with a map of SFUSD and charter schools.">\n'
    '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
    + head + '\n</head>\n<body>\n<div class="wrap" id="page">' + body + '</body>\n</html>\n')
print('page bytes', len(t), 'geo bytes', len(J(GEO)))
