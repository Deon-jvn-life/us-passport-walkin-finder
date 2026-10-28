#!/usr/bin/env python3
"""Place facility coordinates from official State Department data, then Nominatim.

Official coordinates come from the public Consular Affairs locations API
(https://cadataapi.state.gov/api/Passport/Applications/Locations/States/FL).
A pin is kept only when the house number and street match that record.
Anything left over is geocoded from the official street address with
OpenStreetMap Nominatim, at most one request per second.
Results are written to tools/coordinates.json. This script does not invent coordinates.
"""
import json, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = 'SouthFloridaPassportPlaces/1.0 (https://us-passport-walkin-finder.vercel.app; facility map geocoding)'
API = 'https://cadataapi.state.gov/api/Passport/Applications/Locations/States/FL'
NOMINATIM = 'https://nominatim.openstreetmap.org/search'
# South Florida counties in this guide. A point outside this box is not used.
BOX = (25.2, 27.2, -81.05, -79.9)  # south, north, west, east

NUM_WORDS = {
    'FIRST': '1', 'SECOND': '2', 'THIRD': '3', 'FOURTH': '4', 'FIFTH': '5',
    'SIXTH': '6', 'SEVENTH': '7', 'EIGHTH': '8', 'NINTH': '9', 'TENTH': '10',
}

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)

def norm_street(raw):
    """Normalize a street line so two official spellings of the same address can match."""
    s = (raw or '').upper().replace('.', ' ').replace('&', ' AND ')
    s = re.sub(r'\b\d+(ST|ND|RD|TH)\s+FLOOR\b', ' ', s)
    s = re.sub(r'\b(ROOM|RM|STE|SUITE|UNIT|APT|APARTMENT|BLDG|BUILDING|FLOOR|FL)\b.*$', ' ', s)
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\b([NS])\s+([EW])\b', r'\1\2', s)
    repls = [
        ('STREET', 'ST'), ('AVENUE', 'AVE'), ('BOULEVARD', 'BLVD'), ('DRIVE', 'DR'),
        ('ROAD', 'RD'), ('COURT', 'CT'), ('PLACE', 'PL'), ('LANE', 'LN'),
        ('TERRACE', 'TER'), ('CIRCLE', 'CIR'), ('HIGHWAY', 'HWY'), ('PARKWAY', 'PKWY'),
        ('CAUSEWAY', 'CSWY'), ('EXPRESSWAY', 'EXPY'),
        ('NORTHEAST', 'NE'), ('NORTHWEST', 'NW'), ('SOUTHEAST', 'SE'), ('SOUTHWEST', 'SW'),
        ('NORTH', 'N'), ('SOUTH', 'S'), ('EAST', 'E'), ('WEST', 'W'),
        ('STATE ROAD', 'SR'), ('STATE RD', 'SR'),
        ('PROFESSIONAL GOLFERS ASSOCIATION', 'PGA'),
        ('PROFESSIONAL GOLFERS ASSOC', 'PGA'),
        ('MARTIN LUTHER KING JR', 'MLK'), ('MARTIN LUTHER KING', 'MLK'),
        ('DR MLK', 'MLK'), ('U S HWY', 'US HWY'),
    ]
    for a, b in repls:
        s = re.sub(rf'\b{a}\b', b, s)
    for a, b in NUM_WORDS.items():
        s = re.sub(rf'\b{a}\b', b, s)
    # 1ST, 84TH, 183RD stay attached. Do not turn "280 ST" into "280ST".
    s = re.sub(r'\b(\d+)(ST|ND|RD|TH)\b', r'\1', s)
    s = re.sub(r'\bS R\b', 'SR', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def split_house(street):
    m = re.match(r'^(\d+)\s+(.*)$', street or '')
    if not m:
        return None, street or ''
    return m.group(1), m.group(2)

def street_line(addr):
    parts = [p.strip() for p in (addr or '').split(',') if p.strip()]
    if len(parts) >= 4 and re.fullmatch(r'\d{5}', parts[-1]) and parts[-2].upper() in ('FL', 'FLORIDA'):
        return ', '.join(parts[:-3])
    return addr or ''

def in_box(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    s, n, w, e = BOX
    return s <= lat <= n and w <= lon <= e

def official_address(name_unused, raw_addr):
    parts = [p.strip() for p in raw_addr.split(',') if p.strip()]
    z, state, city = parts[-1], parts[-2], parts[-3]
    street = ', '.join(parts[:-3])
    street = re.sub(r'\s+', ' ', street).strip()
    return f'{street.title()}, {city.title()}, {state.upper()} {z}'

def title_keep(s):
    # Keep USPS and directional tokens readable without changing the address.
    return s

def load_facilities():
    return json.load(open(os.path.join(HERE, 'sofla_facilities.json'), encoding='utf-8'))

def match_official(facilities, api):
    indexed = []
    for rec in api:
        if rec.get('StateCode') != 'FL':
            continue
        street = norm_street(street_line(rec.get('StreetAddress') or ''))
        house, rest = split_house(street)
        if not house or not in_box(rec.get('Latitude'), rec.get('Longitude')):
            continue
        indexed.append((house, rest, str(rec.get('ZipCode') or '').strip(), rec, street))
    placed, unplaced = {}, {}
    for f in facilities:
        raw = f['raw'][1]
        parts = [p.strip() for p in raw.split(',') if p.strip()]
        zip_code = parts[-1]
        ours = norm_street(street_line(raw))
        house, rest = split_house(ours)
        address = official_address(f['raw'][0], raw)
        if not house:
            unplaced[f['id']] = {
                'official_address': address,
                'reason': 'The official locator address has no house number, so it was not pinned.',
            }
            continue
        hits = []
        for h, r, z, rec, full in indexed:
            if h != house:
                continue
            if r != rest:
                continue
            zip_ok = z == zip_code
            hits.append((zip_ok, rec, full, z))
        same_zip = [h for h in hits if h[0]]
        chosen = same_zip or []
        if not chosen:
            unplaced[f['id']] = {
                'official_address': address,
                'reason': 'No State Department location record matched this house number, street, and ZIP.',
            }
            continue
        # Same normalized street can appear twice with the same point. Reject if points disagree.
        points = {(round(float(rec['Latitude']), 5), round(float(rec['Longitude']), 5)) for _, rec, _, _ in chosen}
        if len(points) > 1:
            unplaced[f['id']] = {
                'official_address': address,
                'reason': 'More than one official coordinate matched this address, and they disagree.',
            }
            continue
        _, rec, full, z = chosen[0]
        placed[f['id']] = {
            'lat': float(rec['Latitude']),
            'lon': float(rec['Longitude']),
            'source': 'us-department-of-state',
            'source_url': API,
            'official_address': address,
            'matched_name': rec.get('FacilityName') or '',
            'matched_address': f"{rec.get('StreetAddress')}, {rec.get('City')}, {rec.get('StateCode')} {rec.get('ZipCode')}",
            'confidence': 'House number, street, and ZIP match a State Department location record.',
        }
    return placed, unplaced

def nominatim_search(params):
    qs = urllib.parse.urlencode(params)
    url = NOMINATIM + '?' + qs
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)

def accept_nominatim(result, house, rest, zip_code, city):
    if not in_box(result.get('lat'), result.get('lon')):
        return False, 'Result is outside Miami-Dade, Broward, and Palm Beach.'
    addr = result.get('address') or {}
    got_house = re.sub(r'\D', '', str(addr.get('house_number') or ''))
    if got_house != house:
        return False, 'House number did not match.'
    road = norm_street(addr.get('road') or addr.get('pedestrian') or addr.get('footway') or '')
    _, road_rest = split_house(road) if road[:1].isdigit() else (None, road)
    # Road from Nominatim usually has no house number.
    road_rest = norm_street(addr.get('road') or '')
    road_rest = split_house(road_rest)[1] or road_rest
    if road_rest != rest:
        return False, f'Street did not match (got {road_rest or "no street"}).'
    postcode = str(addr.get('postcode') or '')
    locality = ' '.join(str(addr.get(k) or '') for k in ('city', 'town', 'village', 'hamlet', 'suburb', 'municipality')).upper()
    zip_ok = postcode.startswith(zip_code)
    city_ok = city.upper() in locality or locality in city.upper() or city.upper().split()[0] in locality
    if not zip_ok and not city_ok:
        return False, 'ZIP and city did not match.'
    addresstype = result.get('addresstype') or result.get('type') or ''
    if addresstype in ('postcode', 'county', 'state', 'country', 'city', 'town', 'village', 'municipality'):
        return False, 'Result is an area, not the street address.'
    return True, 'House number and street matched the official address in OpenStreetMap.'

def meters(a, b):
    from math import atan2, cos, radians, sin, sqrt
    lat1, lon1 = radians(float(a['lat'])), radians(float(a['lon']))
    lat2, lon2 = radians(float(b['lat'])), radians(float(b['lon']))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371000 * atan2(sqrt(h), sqrt(1 - h))

STOP = {
    'OF', 'THE', 'USPS', 'POST', 'OFFICE', 'BRANCH', 'STATION', 'CITY', 'COUNTY', 'CLERK',
    'COURT', 'COURTS', 'AND', 'COMPTROLLER', 'MAIN', 'FL', 'FLORIDA', 'PO', 'SERVICE',
}

def name_score(result, facility_name):
    label = norm_street(result.get('display_name') or '')
    words = [w for w in re.sub(r'[^A-Z0-9 ]', ' ', (facility_name or '').upper()).split() if len(w) > 2 and w not in STOP]
    score = sum(2 for w in words if w in label.split())
    kind = result.get('addresstype') or result.get('type') or ''
    if kind in ('amenity', 'office', 'library', 'townhall', 'courthouse', 'post_office', 'public'):
        score += 3
    elif kind == 'building':
        score += 1
    return score

def expand_street(street):
    """Same official address, written out so a geocoder can read the abbreviations."""
    s = (street or '').upper().replace('.', ' ')
    s = re.sub(r'\b([NS])\s+([EW])\b', r'\1\2', s)
    s = re.sub(r'\s+', ' ', s).strip()
    words = []
    dirs = {'NW': 'Northwest', 'NE': 'Northeast', 'SW': 'Southwest', 'SE': 'Southeast', 'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West'}
    suffixes = {'ST': 'Street', 'AVE': 'Avenue', 'BLVD': 'Boulevard', 'RD': 'Road', 'DR': 'Drive', 'LN': 'Lane', 'CT': 'Court', 'PL': 'Place', 'HWY': 'Highway', 'PKWY': 'Parkway', 'CSWY': 'Causeway'}
    for w in s.split():
        m = re.fullmatch(r'(\d+)(ST|ND|RD|TH)', w)
        if m:
            n = int(m.group(1))
            if n % 100 in (11, 12, 13):
                ending = 'th'
            else:
                ending = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            words.append(f'{n}{ending}')
        elif w in dirs:
            words.append(dirs[w])
        elif w in suffixes:
            words.append(suffixes[w])
        else:
            words.append(w.title())
    return ' '.join(words)

def choose_result(results, house, rest, zip_code, city, facility_name):
    good, reasons = [], []
    for result in results or []:
        ok, why = accept_nominatim(result, house, rest, zip_code, city)
        if ok:
            good.append(result)
        else:
            reasons.append(f"{why} [{(result.get('display_name') or '')[:90]}]")
    if not good:
        if reasons:
            return None, reasons[0]
        return None, 'No OpenStreetMap result for this address.'
    ranked = sorted(good, key=lambda r: name_score(r, facility_name), reverse=True)
    best = ranked[0]
    best_score = name_score(best, facility_name)
    tied = [r for r in ranked if name_score(r, facility_name) == best_score]
    if any(meters(best, r) > 75 for r in tied):
        return None, 'OpenStreetMap returned separate points for this address, so it was not pinned.'
    if best_score == 0 and any(meters(best, r) > 75 for r in good):
        return None, 'OpenStreetMap returned separate points for this address, so it was not pinned.'
    return best, None

def geocode_one(address, city, zip_code, street_raw, facility_name):
    house, rest = split_house(norm_street(street_raw))
    if not house:
        return None, 'The official address has no house number.'
    free = f'{street_raw}, {city}, FL {zip_code}'
    expanded = f'{expand_street(street_raw)}, {city}, FL {zip_code}'
    attempts = [
        {'street': street_raw, 'city': city, 'state': 'Florida', 'postalcode': zip_code, 'country': 'United States'},
        {'q': free},
    ]
    if expanded.lower() != free.lower():
        attempts.append({'q': expanded})
    last_reason = 'No OpenStreetMap result for this address.'
    for params in attempts:
        params = dict(params)
        params.update({'format': 'jsonv2', 'addressdetails': 1, 'limit': 5, 'countrycodes': 'us'})
        try:
            results = nominatim_search(params)
        except Exception as exc:
            return None, f'Nominatim request failed ({exc.__class__.__name__}).'
        time.sleep(1.1)
        best, why = choose_result(results, house, rest, zip_code, city, facility_name)
        if not best:
            last_reason = why
            continue
        return {
            'lat': float(best['lat']),
            'lon': float(best['lon']),
            'source': 'openstreetmap-nominatim',
            'source_url': 'https://nominatim.openstreetmap.org/',
            'matched_label': best.get('display_name') or '',
            'osm_type': best.get('osm_type') or '',
            'osm_id': best.get('osm_id'),
            'confidence': 'House number and street matched the official address in OpenStreetMap.',
        }, None
    return None, last_reason

def main():
    facilities = load_facilities()
    print('Fetching State Department locations...')
    api = fetch(API)
    placed, pending = match_official(facilities, api)
    print(f'Official matches: {len(placed)}. Still to geocode: {len(pending)}.')
    unplaced = {}
    for f in facilities:
        if f['id'] not in pending:
            continue
        parts = [p.strip() for p in f['raw'][1].split(',') if p.strip()]
        zip_code, city = parts[-1], parts[-3]
        street = street_line(f['raw'][1])
        # Drop the unit so the geocoder sees the street address. The unit stays in official_address.
        street_query = re.sub(r'\b\d+(ST|ND|RD|TH)\s+FLOOR\b', ' ', street, flags=re.I)
        street_query = re.sub(r'\b(ROOM|RM|STE|SUITE|UNIT|APT|APARTMENT|BLDG|BUILDING)\b.*$', ' ', street_query, flags=re.I)
        street_query = re.sub(r'\s+', ' ', street_query).strip(' ,')
        address = pending[f['id']]['official_address']
        print('NOMINATIM', f['id'], street_query, city, zip_code)
        found, reason = geocode_one(address, city.title(), zip_code, street_query, f['raw'][0])
        if found:
            found['official_address'] = address
            placed[f['id']] = found
            print('  OK', found['lat'], found['lon'], found['matched_label'][:120])
        else:
            unplaced[f['id']] = {'official_address': address, 'reason': reason, 'name': f['raw'][0]}
            print('  SKIP', reason)
    # Miami Passport Agency is listed from travel.state.gov, not the acceptance-facility file.
    agency_address = '1501 Biscayne Blvd, Suite 400, Miami, FL 33132'
    print('NOMINATIM miami-passport-agency')
    found, reason = geocode_one(agency_address, 'Miami', '33132', '1501 Biscayne Blvd', 'Miami Passport Agency')
    agency = None
    if found:
        found['official_address'] = agency_address
        found['name'] = 'Miami Passport Agency'
        agency = found
        print('  OK', found['lat'], found['lon'], found['matched_label'][:140])
    else:
        print('  SKIP', reason)
    # Reviewed by hand after Nominatim. Applied only when a place is still unplaced,
    # so a later confident match is not overwritten.
    review = {
        'uj': 'The locator address is 67959 SW 196th Ave. OpenStreetMap has no result for that house number. The State Department locations API lists Everglades Post Office at 6759 SW 196th Ave, a different house number, so that coordinate was not used.',
        'vb': 'The locator street is N Haverhill Rd. OpenStreetMap has no result for that street. The State Department locations API lists Haverhill Post Office at 3900 Haverhill Blvd. Road and boulevard do not match, so that coordinate was not used.',
        '3x7': 'The locator address is 110 Dr MLK Blvd West. OpenStreetMap has both 110 Southwest Martin Luther King Boulevard and 110 Southeast Martin Luther King Boulevard. The locator line does not say which street, so no pin was added.',
        '53s': 'OpenStreetMap has no result for 14850 SW 280 Street, Homestead, FL 33032.',
        '5ag': 'OpenStreetMap has no house number for 1601 NE 164th Street. A library point at 1601 Northeast 16th Avenue is a different street, so it was not used.',
    }
    for fid, reason in review.items():
        if fid in unplaced:
            unplaced[fid]['reason'] = reason
    out = {
        'note': 'Coordinates are copied from the U.S. Department of State passport locations API when the house number, street, and ZIP match. Other points come from geocoding the official street address with OpenStreetMap Nominatim. Unplaced locations have no pin.',
        'state_department_url': API,
        'nominatim_url': 'https://nominatim.openstreetmap.org/',
        'places': placed,
        'unplaced': unplaced,
        'miami_passport_agency': agency if agency else {'official_address': agency_address, 'reason': reason},
    }
    dest = os.path.join(HERE, 'coordinates.json')
    json.dump(out, open(dest, 'w', encoding='utf-8'), indent=1)
    dest_end = open(dest, encoding='utf-8').read()
    if not dest_end.endswith('\n'):
        open(dest, 'a', encoding='utf-8').write('\n')
    print('WROTE', dest, 'placed', len(placed), 'unplaced', len(unplaced))

if __name__ == '__main__':
    main()
