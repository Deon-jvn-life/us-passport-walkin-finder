#!/usr/bin/env python3
"""Build the South Florida passport acceptance facility site from JSON in tools/ into site/."""
import json,os,re,html as H,shutil,sys,struct,zlib,urllib.parse
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE); OUT=os.path.join(ROOT,'site')
sys.path.insert(0, HERE)
from sitelib import Site, esc, href, slug
D="26 October 2026"; BASE="https://us-passport-walkin-finder.vercel.app"  # replace with real domain before deploy
# Optional search-console tokens. Leave empty to omit the meta tags.
GOOGLE_SITE_VERIFICATION="XA7XgB_UwrIRvQyNVsnWpSyTyaU6e3-v4g4RBw8RAVI"
MSVALIDATE_01=""
SITE_NAME="South Florida Passport Places"
DISCLAIMER="For general information only. This independent site is not affiliated with the U.S. Department of State or any government agency. Information can change and may contain errors; always confirm with the official source before you act. Nothing here is legal or professional advice, and we accept no liability for decisions made using it."
SHORT_DISCLAIMER="For general information only. This independent site is not affiliated with the U.S. Department of State or any government agency."
MONTHS={'January':'01','February':'02','March':'03','April':'04','May':'05','June':'06','July':'07','August':'08','September':'09','October':'10','November':'11','December':'12'}
def iso_date(when):
    d,m,y=when.split(); return f'{y}-{MONTHS[m]}-{int(d):02d}'
def clean(path):
    if path.endswith('index.html'):
        rest=path[:-len('index.html')]
        return '/'+rest if rest else '/'
    return '/'+path
def plain(s):
    return re.sub(r'\s+',' ',H.unescape(re.sub(r'<[^>]+>','',s))).strip()
def warn_meta(path,title,desc):
    loc=clean(path)
    if not 50<=len(title)<=60: print(f'WARNING: title length {len(title)} outside 50-60 for {loc}: {title}', file=sys.stderr)
    if not 120<=len(desc)<=160: print(f'WARNING: description length {len(desc)} outside 120-160 for {loc}: {desc}', file=sys.stderr)
GROUPS=[
 ("Find a place",[('counties/miami-dade/index.html','Miami-Dade County'),('counties/broward/index.html','Broward County'),('counties/palm-beach/index.html','Palm Beach County'),('walk-in-vs-appointment/index.html','Walk-in or appointment')]),
 ("What to bring",[('fees-and-documents/index.html','Fees and documents'),('urgent-travel/index.html','Urgent travel'),('child-under-16/index.html','Child under 16')]),
 ("Using this guide",[('faq/index.html','Common questions'),('find/index.html','All pages'),('disclaimer/index.html','Disclaimer')])]
STAGE={p:g for g,items in GROUPS for p,_t in items}
ORDER=['fees-and-documents/index.html','urgent-travel/index.html','child-under-16/index.html','walk-in-vs-appointment/index.html']
S=dict(pafl="https://passportfacilitylocator.travel.state.gov/",pafldata="https://passportfacilitylocator.travel.state.gov/data/Facilities.json",
 fees="https://travel.state.gov/content/travel/en/passports/how-apply/fees.html",times="https://travel.state.gov/content/travel/en/passports/how-apply/processing-times.html",
 adult="https://travel.state.gov/content/travel/en/passports/need-passport/apply-in-person.html",child="https://travel.state.gov/content/travel/en/passports/need-passport/under-16.html",
 under16="https://travel.state.gov/en/passports/apply/child/under-16.html",teen="https://travel.state.gov/en/passports/apply/child/16-17-year-old.html",
 forms="https://travel.state.gov/en/passports/apply/help/forms.html",citizenship="https://travel.state.gov/en/passports/apply/help/citizenship-evidence.html",
 photohelp="https://travel.state.gov/en/passports/apply/help/photos.html",
 renew="https://travel.state.gov/content/travel/en/passports/have-passport/renew.html",photos="https://travel.state.gov/content/travel/en/passports/how-apply/photos.html",
 miami="https://travel.state.gov/en/passports/apply/get-fast/make-appointment/miami.html",agency="https://travel.state.gov/en/passports/apply/get-fast/make-appointment.html",
 miami_old="https://travel.state.gov/content/travel/en/passports/get-fast/passport-agencies/miami.html",
 life="https://travel.state.gov/en/passports/apply/get-fast/life-or-death-emergencies.html",
 life_old="https://travel.state.gov/content/travel/en/passports/get-fast/emergencies.html",
 fast="https://travel.state.gov/en/passports/apply/get-fast.html",
 where="https://travel.state.gov/en/passports/apply/help/where-to-apply.html",
 fees_en="https://travel.state.gov/en/passports/apply/help/fees.html",
 times_en="https://travel.state.gov/en/passports/apply/help/processing-time.html",
 status="https://passportstatus.state.gov/",
 adults_en="https://travel.state.gov/en/passports/apply/adults.html",
 renew_en="https://travel.state.gov/en/passports/renew-replace/mail.html",
 broward="https://www.browardclerk.org/Divisions/Passports",pbc="https://www.mypalmbeachclerk.com/services/passports",pbcfees="https://www.mypalmbeachclerk.com/about-us/fees/other-services-fees/passport-fees",
 mdpls="https://mdpls.org/passport",usps="https://www.usps.com/scheduler",census="https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt")
def src(*k): return ' <span class="src">['+', '.join(f'<a href="{S[x]}" rel="noopener">source</a>' for x in k)+']</span>'
DAYS=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
def t12(s):
    h,m=s.split(':'); h=int(h); return f"{12 if h%12==0 else h%12}:{m} {'a.m.' if h<12 else 'p.m.'}"
def parse(hours):
    """Decode the locator hours string exactly as the official locator front end does.
    segment = days,open-close-lunchStart-lunchEnd-flag ; days 0=Monday..6=Sunday ; flag 0 = walk-in (locator 'walk-in hours' filter), 1 or 3 = 'By Appointment', 2 = not walk-in per locator logic."""
    out={}
    for seg in (hours or '').split(';'):
        if ',' not in seg: continue
        ds,rest=seg.split(',',1); p=rest.split('-')
        if len(p)<5 or not p[0] or not p[1] or (p[0]=='00:00' and p[1]=='00:00'): continue
        f=int(p[4] or 0); txt=f"{t12(p[0])} to {t12(p[1])}"
        if p[2] and p[3] and p[2]!=p[3] and ':' in p[2] and ':' in p[3] and f not in (2,3): txt+=f" (closed {t12(p[2])} to {t12(p[3])})"
        for d in ds:
            if d.isdigit() and int(d)<7: out[int(d)]=(txt,f)
    return out
FEAT=lambda b:{'Accessible':bool(b&1),'Photos on site':bool(b&2),'Photos nearby':bool(b&4)}
# Locator website fields that no longer open the facility's own passport page.
REDIRECTS={
 'https://coralgables.com/passports':'https://www.coralgables.com/passport',
 'https://www.cityofwestmiami.gov':'https://cityofwestmiami.gov/index.asp?SEC=9B066478-6E25-403F-876D-3BFDF7EAEC72',
 'https://www.northmiamifl.gov':'https://www.northmiamifl.gov/162/City-Clerks-Office',
 'https://www.ppines.com':'https://www.ppines.com/153/Passport-Office',
 'https://miramarfl.gov':'https://www.miramarfl.gov/Departments/City-Clerk/U.S.-Passports',
}
fac=json.load(open(os.path.join(HERE,'sofla_facilities.json')))
extra=json.load(open(os.path.join(HERE,'official_pages.json')))
COORD=json.load(open(os.path.join(HERE,'coordinates.json'),encoding='utf-8'))
COUNTIES={"miami-dade":"Miami-Dade County","broward":"Broward County","palm-beach":"Palm Beach County"}
recs=[]
APPT=re.compile(r'appointment[s]? (only|required)|by appointment|no longer offer walk-in|walk-in customers are not accepted',re.I)
WALK=re.compile(r'walk[- ]?in',re.I)
for f in fac:
    n,addr,ph,web,feat,hrs,com=(f['raw']+[None]*7)[:7]
    parts=[p.strip() for p in addr.split(',') if p.strip()]; z=parts[-1]; st=parts[-2]; city=parts[-3]; street=', '.join(parts[:-3])
    h=parse(hrs); walk=any(v[1]==0 for v in h.values()); appt_only=bool(h) and all(v[1]!=0 for v in h.values())
    com=(com or '').strip()
    conflict=''
    if walk and com and re.search(r'appointment[s]? only|appointments only|appointment required|appointments required|appointment only',com,re.I): conflict='Locator hours are flagged walk-in, but the locator comment says appointments only or required.'
    if not walk and com and re.search(r'walk[- ]?ins? (are )?acc[ep]|walk-ins monday|accept walk-ins',com,re.I): conflict='Locator comment mentions walk-ins, but all listed hours are flagged by appointment.'
    kind='USPS' if ('USPS' in n or 'POST OFFICE' in n or 'usps.com' in (web or '') ) else ('Clerk of Court' if 'CLERK OF' in n and 'COURT' in n else ('Library' if 'LIBRARY' in n else 'Municipal or other government office'))
    w=(web or '').strip().rstrip('.,;')
    if '@' in w or not re.match(r'^https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,}',w,re.I): w=''
    else: w=w.lower()
    w=REDIRECTS.get(w,w)
    recs.append(dict(id=f['id'],name=n.title().replace('Usps','USPS').replace('Po ','PO ').replace("'S","'s"),street=street.title(),city=city.title(),zip=z,county=f['county'],
      phone=re.sub(r'(\d{3})(\d{3})(\d{4})',r'(\1) \2-\3',ph or '') or 'Not stated by source',web=w,feat=FEAT(int(feat or 0)),hours=h,walk=walk,appt_only=appt_only,
      comment=com,conflict=conflict,kind=kind,raw_hours=hrs))
for r in recs:
    for e in extra:
        if e['match'] in r['name'].upper() and e['county']==r['county'] and e['url'] not in [x['url'] for x in r.get('official',[])]: r.setdefault('official',[]).append(e)
for r in recs:
    for e in r.get('official',[]):
        if e.get('walkin') is False and r['walk']: r['conflict']=(r['conflict']+' ' if r['conflict'] else '')+f"The operator page says walk-ins are not accepted, but locator hours for this office are flagged walk-in."
def add_conflict(pred,text):
    for r in recs:
        if pred(r): r['conflict']=(r['conflict']+' ' if r['conflict'] else '')+text
add_conflict(lambda r:'South Regional' in r['name'] and r['county']=='Broward County',"The clerk page lists phone (954) 831-0320. The locator still lists (954) 831-0350.")
add_conflict(lambda r:'West Regional' in r['name'] and r['county']=='Broward County',"The clerk page lists phone (954) 831-6528. The locator still lists (954) 831-2391.")
add_conflict(lambda r:'North Dade Regional' in r['name'],"The library page lists Monday passport hours as 4:30 p.m. to 7:30 p.m. The locator lists Monday as 11:30 a.m. to 7:30 p.m.")
add_conflict(lambda r:'Miami Springs' in r['name'],"The city page lists Saturday as 8:00 a.m. to 2:00 p.m. The locator lists Saturday as 8:00 a.m. to 12:00 p.m. The city page says a walk-in may not be served the same day.")
add_conflict(lambda r:r['name'].startswith('City Of West Miami'),"The city page lists Monday to Friday until 4:00 p.m. (last appointment 3:30 p.m.) and Tuesday until 6:00 p.m. (last appointment 5:30 p.m.). The locator lists later closing times.")
add_conflict(lambda r:'Miami Beach - Finance' in r['name'],"The city page says passport hours run until 1:30 p.m. The locator lists those days until 2:00 p.m.")
add_conflict(lambda r:r['name'].startswith('City Of Miramar'),"The city page says passport appointments run until 5:00 p.m. Monday to Thursday. The locator lists shorter hours and a midday closure.")
for r in recs:
    if 'South Regional' in r['name'] and r['county']=='Broward County': r['phone']='(954) 831-0320'
    if 'West Regional' in r['name'] and r['county']=='Broward County': r['phone']='(954) 831-6528'
    if 'Miami Springs' in r['name'] and not r['web']: r['web']='https://www.miamisprings-fl.gov/cityclerk/page/miami-springs-passport-services-0'
json.dump(recs,open(os.path.join(HERE,'facilities_parsed.json'),'w'),indent=1)
def page(path,title,body,desc,checked=None,crumb=None,home=False,error=False,faq_items=None,long_page=False):
    when=checked or D
    site.checked[path]=(when, iso_date(when))
    warn_meta(path,title,desc)
    kind='home' if home else ('error' if error else 'article')
    stage=None if home or error else STAGE.get(path)
    site.page(path,title,desc,body,stage=stage,kind=kind,faqs=faq_items,long_page=long_page,crumb=crumb)
def hrs_html(h):
    if not h: return 'Not stated by source'
    return '<br>'.join(f"{DAYS[d][:3]}: {v[0]} <span class='lv {'ok' if v[1]==0 else 'comm'}'>{'walk-in' if v[1]==0 else 'appointment'}</span>" for d,v in sorted(h.items()))
def table(rows,showcounty=False):
    t=('<div class="filterbox"><label for="facility-q">Filter by city, ZIP or name</label><input id="facility-q" type="search" autocomplete="off" oninput="var v=this.value.toLowerCase();document.querySelectorAll(\'table tr\').forEach(function(r){if(r.querySelector(\'td\'))r.style.display=r.textContent.toLowerCase().indexOf(v)>-1?\'\':\'none\'})"></div>'
       '<div class="wrap" tabindex="0" aria-label="Facility table"><table><tr><th scope="col">Facility</th><th scope="col">Address</th>'+('<th scope="col">County</th>' if showcounty else '')+'<th scope="col">Acceptance hours (locator)</th><th scope="col">Walk-in?</th><th scope="col">Phone / website</th><th scope="col">Notes and source</th></tr>')
    for r in sorted(rows,key=lambda x:(x['city'],x['name'])):
        wk='Yes, some hours' if r['walk'] else ('No, appointment flagged for all listed hours' if r['appt_only'] else 'Not stated by source')
        ft=', '.join(k for k,v in r['feat'].items() if v) or 'None flagged'
        o=''.join(f'<br><span class="src">{H.escape(e["fact"])} [<a href="{e["url"]}" rel="noopener">operator page</a>]</span>' for e in r.get('official',[]))
        cf=f'<br><span class="lv comm">Conflict</span> <span class="src">{H.escape(r["conflict"])}</span>' if r['conflict'] else ''
        web=f'<br><a href="{H.escape(r["web"])}" rel="noopener">website</a>' if r['web'] else ''
        t+=f'<tr><td><strong>{H.escape(r["name"])}</strong><br><span class="src">{r["kind"]}</span></td><td>{H.escape(r["street"])}<br>{H.escape(r["city"])}, FL {r["zip"]}<br>{directions_html(postal_address(r), r["name"])}</td>'+(f'<td>{r["county"]}</td>' if showcounty else '')+f'<td>{hrs_html(r["hours"])}</td><td>{wk}</td><td>{r["phone"]}{web}</td><td><span class="src">Locator comment: "{H.escape(r["comment"]) or "none"}". Features: {ft}.</span>{o}{cf} <span class="src">[<a href="{S["pafl"]}" rel="noopener">source</a>]</span></td></tr>'
    return t+'</table></div>'
def postal_address(r):
    return f"{r['street']}, {r['city']}, FL {r['zip']}"
def directions_href(address):
    return 'https://www.google.com/maps/dir/?api=1&destination=' + urllib.parse.quote(address, safe='')
def directions_html(address, name):
    url=directions_href(address)
    if ' ' in url or not url.startswith('https://www.google.com/maps/dir/?api=1&destination='):
        raise SystemExit('Bad directions link')
    hidden=f' to {name}, opens in a new tab'
    return f'<a class="directions" href="{H.escape(url, quote=True)}" target="_blank" rel="noopener">Get directions<span class="visually-hidden">{H.escape(hidden)}</span></a>'
def point_ok(p):
    if not isinstance(p, dict): return False
    lat,lon=p.get('lat'),p.get('lon')
    if isinstance(lat, bool) or isinstance(lon, bool): return False
    if not isinstance(lat,(int,float)) or not isinstance(lon,(int,float)): return False
    return 25.2<=float(lat)<=27.2 and -81.05<=float(lon)<=-79.9
AGENCY_ADDRESS='Omni Center, 1501 Biscayne Blvd, Suite 400, Miami, FL 33132'
def map_points(rows, include_agency=False):
    pts=[]
    for r in rows:
        p=COORD['places'].get(r['id'])
        if not point_ok(p): continue
        address=postal_address(r)
        pts.append({'name':r['name'],'address':address,'lat':p['lat'],'lon':p['lon'],'directions':directions_href(address)})
    agency=COORD.get('miami_passport_agency') or {}
    if include_agency and point_ok(agency):
        pts.append({'name':'Miami Passport Agency','address':AGENCY_ADDRESS,'lat':agency['lat'],'lon':agency['lon'],'directions':directions_href(AGENCY_ADDRESS)})
    return pts
def map_block(rows, label, include_agency=False):
    pts=map_points(rows, include_agency)
    if not pts: return ''
    missing=[r for r in rows if not point_ok(COORD['places'].get(r['id']))]
    data=json.dumps(pts, ensure_ascii=True, separators=(',', ':')).replace('<','\\u003c')
    omitted=''
    note='The list is the main information. The map is an extra view. Click the map to zoom with the scroll wheel. Before that, scrolling moves the page.'
    if include_agency:
        note='The list is the main information. The map is an extra view of those places, plus the Miami Passport Agency. Click the map to zoom with the scroll wheel. Before that, scrolling moves the page.'
    if missing:
        names=', '.join(H.escape(r['name']) for r in missing)
        omitted=f'<p>These places are in the list and not on the map: {names}.</p>'
    return (
        '<div class="loc-map">'
        f'<p id="map-note">{note}</p>'
        f'<div id="facility-map" class="loc-map-canvas" role="region" tabindex="0" aria-label="{H.escape(label)}" aria-describedby="map-note" data-leaflet="/vendor/leaflet/leaflet.js" data-leaflet-css="/vendor/leaflet/leaflet.css">{len(pts)} places. The map loads when this part of the page is on screen. The list has every place.</div>'
        f'<script type="application/json" id="facility-map-data">{data}</script>'
        f'<p class="src">Map data from <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap</a> contributors.</p>'
        f'{omitted}</div><script src="/map.js" defer></script>'
    )
MIAMI=f'''<div class="card"><strong>Miami Passport Agency (urgent travel only)</strong><p>Omni Center, 1501 Biscayne Blvd, Suite 400, Miami, FL 33132. {directions_html(AGENCY_ADDRESS, 'the Miami Passport Agency')}</p><p>Monday to Friday 7:00 a.m. to 2:00 p.m., closed weekends and federal holidays. By appointment only. Miami is in a State Department pilot with the Detroit and San Juan passport agencies: you can make an appointment for urgent international travel within 21 calendar days, or if you need a foreign visa within 28 calendar days. Appointments: 877-487-2778{src('miami')}. This is not an acceptance facility; routine applications go to the places listed on this site. <a href="/urgent-travel/">Who can book, what to bring, and how this differs from expedited service</a>.</p></div>'''
CALL='<div class="card note"><strong>Call or check online before you go.</strong> The locator says to check with the facility whether you need an appointment{0}. USPS locations direct you to usps.com/scheduler{1}. Hours below are as published in the official locator data on the date shown.</div>'.format(src('adult'),src('usps'))
cc={k:[r for r in recs if r['county']==v] for k,v in COUNTIES.items()}
nwalk=sum(r['walk'] for r in recs); ncon=sum(1 for r in recs if r['conflict'])
CSS=open(os.path.join(HERE,'style.css'),encoding='utf-8').read()
NOTICE=f'{H.escape(SHORT_DISCLAIMER)} <a href="/disclaimer/">Full disclaimer</a>.'
FOOT=(f'<p>Independent, unofficial guide. Not affiliated with the U.S. Department of State, USPS, any clerk of court or library. We do not sell or promote expediting services. Facility data comes from the official Passport Acceptance Facility Locator{src("pafl")}; rules and fees from travel.state.gov. Always confirm hours with the facility before you go. Last checked: {D}.</p>'
      f'<p>{H.escape(DISCLAIMER)}</p><p><a href="/disclaimer/">Disclaimer</a></p>'
      '<p class="related">Related guides: <a href="https://south-florida-dmv-walkin-guide.vercel.app/" rel="noopener">South Florida DMV walk-in guide</a> and <a href="https://south-florida-dog-beaches.vercel.app/" rel="noopener">South Florida dog beaches</a>.</p>')
site=Site(ROOT, BASE, SITE_NAME, GROUPS, ORDER, FOOT, CSS, NOTICE, gsc=GOOGLE_SITE_VERIFICATION)
def county_sum(k):
    rows=cc[k]
    return f'{len(rows)} facilities in the official locator, {sum(r["walk"] for r in rows)} with at least some hours flagged walk-in. County is assigned from the facility ZIP code. Call or check online before you go.'
site.summaries={
 'index.html':f'{len(recs)} passport acceptance facilities in Miami-Dade, Broward and Palm Beach, with acceptance hours and whether those hours are walk-in or appointment.',
 'counties/miami-dade/index.html':county_sum('miami-dade'),
 'counties/broward/index.html':county_sum('broward'),
 'counties/palm-beach/index.html':county_sum('palm-beach'),
 'walk-in-vs-appointment/index.html':f'On {D}, {nwalk} of {len(recs)} South Florida facilities have at least some walk-in hours. The rest are appointment-flagged for all listed hours. {ncon} have a conflict between the locator\'s walk-in flag and the comment text or the operator\'s own page.',
 'fees-and-documents/index.html':f'All amounts as stated by travel.state.gov on {D}. This page covers which form to use, the fees, how to pay, the documents to bring, the photo rules and the processing times.',
 'urgent-travel/index.html':'The Miami Passport Agency takes urgent-travel appointments. Its page allows booking within 21 calendar days of travel, or 28 if you need a foreign visa. Other State Department pages still say 14 days. Bring printed proof of travel. You cannot walk in.',
 'child-under-16/index.html':'A child under 16 applies in person with Form DS-11. Bring the child. Both parents or guardians go, or you bring the consent or custody documents on this page. You cannot renew a child\'s passport, and the passport is valid for 5 years.',
 'faq/index.html':'Short sourced answers on walk-in hours, fees, documents and applying for a U.S. passport in Miami-Dade, Broward and Palm Beach.',
 'find/index.html':'Every page on this guide, grouped by topic.',
 'disclaimer/index.html':'For general information only. This independent site is not affiliated with the U.S. Department of State or any government agency. Always confirm with the official source before you act.',
}
site.aliases={
 'index.html':'home start passport south florida',
 'counties/miami-dade/index.html':'miami dade county post office library clerk zip',
 'counties/broward/index.html':'broward county fort lauderdale hollywood deerfield',
 'counties/palm-beach/index.html':'palm beach county west palm delray',
 'walk-in-vs-appointment/index.html':'walk-in walk in appointment hours usps post office',
 'fees-and-documents/index.html':'fees cost ds-11 ds-82 photo documents processing form',
 'urgent-travel/index.html':'miami passport agency urgent appointment life-or-death expedite 21 days proof of travel cruise emergency',
 'child-under-16/index.html':'child minor under 16 ds-3053 consent parents baby',
 'faq/index.html':'faq questions answers frequently asked',
 'find/index.html':'search index all pages find',
 'disclaimer/index.html':'disclaimer liability warranty not affiliated',
}
site.read_next={
 'index.html':['urgent-travel/index.html','walk-in-vs-appointment/index.html','fees-and-documents/index.html'],
 'counties/miami-dade/index.html':['urgent-travel/index.html','counties/broward/index.html','walk-in-vs-appointment/index.html'],
 'counties/broward/index.html':['counties/miami-dade/index.html','counties/palm-beach/index.html','walk-in-vs-appointment/index.html'],
 'counties/palm-beach/index.html':['counties/miami-dade/index.html','counties/broward/index.html','fees-and-documents/index.html'],
 'walk-in-vs-appointment/index.html':['urgent-travel/index.html','fees-and-documents/index.html','faq/index.html'],
 'fees-and-documents/index.html':['urgent-travel/index.html','child-under-16/index.html','walk-in-vs-appointment/index.html'],
 'urgent-travel/index.html':['fees-and-documents/index.html','counties/miami-dade/index.html','child-under-16/index.html'],
 'child-under-16/index.html':['urgent-travel/index.html','fees-and-documents/index.html','walk-in-vs-appointment/index.html'],
 'faq/index.html':['urgent-travel/index.html','fees-and-documents/index.html','walk-in-vs-appointment/index.html'],
 'find/index.html':['walk-in-vs-appointment/index.html','fees-and-documents/index.html','faq/index.html'],
 'disclaimer/index.html':['faq/index.html','fees-and-documents/index.html','find/index.html'],
 '404.html':['walk-in-vs-appointment/index.html','fees-and-documents/index.html','faq/index.html'],
}
def jump(path, label=None):
    title=label or site.titles[path]
    blurb=site.summaries.get(path,'')
    extra=f'<span class="ls">{esc(blurb)}</span>' if blurb else ''
    return f'<a class="jump" href="{href(path)}"><span class="lt">{esc(title)}</span>{extra}</a>'
topics=''.join(
    f'<section class="topic"><h3 id="{slug(g)}">{esc(g)}</h3><ul class="link-grid">'+''.join(f'<li>{jump(p)}</li>' for p,_t in items)+'</ul></section>'
    for g,items in GROUPS)
body=f'''<h1>Where to apply for a U.S. passport in South Florida</h1><p>{len(recs)} passport acceptance facilities in Miami-Dade, Broward and Palm Beach counties, from the State Department's official locator data on {D}{src('pafl')}, with acceptance hours and whether those hours are walk-in or appointment.</p>{CALL}
<h2>Start here</h2><p>Read these pages in this order, then choose a county.</p><ol class="steps"><li><a href="/fees-and-documents/">Fees, DS-11 vs DS-82, documents, photos, processing times</a></li><li><a href="/child-under-16/">Passport for a child under 16: consent, documents and fees</a></li><li><a href="/walk-in-vs-appointment/">Walk-in vs appointment: every facility with walk-in hours</a></li></ol>
<h2>Top tasks</h2><ul class="tasks"><li><a href="/urgent-travel/">Urgent travel: Miami Passport Agency appointments</a></li><li><a href="/walk-in-vs-appointment/">Walk-in vs appointment: every facility with walk-in hours</a></li><li><a href="/fees-and-documents/">Fees, DS-11 vs DS-82, documents, photos, processing times</a></li><li><a href="/child-under-16/">Passport for a child under 16: consent, documents and fees</a></li><li><a href="/faq/">FAQ</a></li></ul>
<h2>By county</h2><ul class="grid">'''+''.join(f'<li><a href="/counties/{k}/">{v}</a> ({len(cc[k])} facilities, {sum(r["walk"] for r in cc[k])} with some walk-in hours)</li>' for k,v in COUNTIES.items())+f'''</ul>
<h2>Who needs to apply in person</h2><div class="card"><ul><li>First-time adult applicants, and adults whose passport was lost, stolen or damaged, issued over 15 years ago, or issued when they were under 16, must apply in person with Form DS-11{src('adult')}.</li>
<li>All children under 16 must apply in person, usually with both parents or guardians{src('child')}. <a href="/child-under-16/">What to bring for a child under 16</a>.</li><li>Eligible adults can renew by mail (DS-82) or online, and postal employees should not charge the $35 facility fee for a DS-82 renewal{src('renew')}.</li></ul></div>
{MIAMI}
<h2>All topics</h2><p>Every page on this guide, grouped by topic.</p>{topics}'''
page('index.html',"South Florida passport acceptance facilities, walk-in hours",body,"Passport acceptance facilities in Miami-Dade, Broward and Palm Beach with walk-in vs appointment hours, from official State Department locator data.",home=True)
for k,v in COUNTIES.items():
    note=''.join(f'<div class="card"><strong>{H.escape(e["title"])}</strong><p>{H.escape(e["fact"])} <span class="src">[<a href="{e["url"]}" rel="noopener">source</a>]</span></p></div>' for e in {x['title']:x for x in extra if x['county']==v}.values())
    b=f'<h1>Passport acceptance facilities in {v}</h1><p>{len(cc[k])} facilities in the official locator, {sum(r["walk"] for r in cc[k])} with at least some hours flagged walk-in. County is assigned from the facility ZIP code using the Census 2020 ZCTA to county file{src("census")}.</p><h2>Check before you go</h2>{CALL}'
    if note: b+=f'<h2>What operator pages say</h2>{note}'
    map_label=f'Map of passport acceptance facilities in {v}'
    if k=='miami-dade': map_label='Map of passport places in Miami-Dade County, including the Miami Passport Agency'
    b+=f'<p>Applying for a child under 16: <a href="/child-under-16/">both parents, the consent form, documents and fees</a>.</p><h2>Facility list</h2>'+map_block(cc[k], map_label, include_agency=(k=='miami-dade'))+table(cc[k])
    if k=='miami-dade': b+=f'<h2>Urgent travel only</h2>{MIAMI}'
    page(f'counties/{k}/index.html',f"Passport acceptance facilities in {v}, FL",b,f"Passport acceptance facilities in {v} with hours, walk-in or appointment, from official State Department locator data.",crumb=v,long_page=True)
wr=[r for r in recs if r['walk']]
b=f'''<h1>Passport walk-in vs appointment in South Florida</h1>
<div class="card"><p>The official locator marks each block of acceptance hours. Its "Walk-in hours" filter counts only hours not flagged "By Appointment"{src('pafl')}. On {D}: <strong>{nwalk}</strong> of {len(recs)} South Florida facilities have at least some walk-in hours; the rest are appointment-flagged for all listed hours. Every USPS location in the data shows "To schedule a passport appointment or view additional passport acceptance times, please visit www.usps.com/scheduler."{src('usps')}</p>
<p>{ncon} facilities have a conflict between the locator's walk-in flag and the comment text or the operator's own page. They are marked Conflict below. Trust the operator and call.</p></div>
<h2>Facilities with some walk-in hours</h2>{map_block(wr, 'Map of South Florida passport facilities with walk-in hours, and the Miami Passport Agency', include_agency=True)}{table(wr,True)}
<h2>What operators say on their own pages</h2>'''+''.join(f'<div class="card"><strong>{H.escape(e["title"])}</strong><p>{H.escape(e["fact"])} <span class="src">[<a href="{e["url"]}" rel="noopener">source</a>]</span></p></div>' for e in {x['title']:x for x in extra}.values())+MIAMI
page('walk-in-vs-appointment/index.html',"Passport walk-in vs appointment hours in South Florida",b,"Which South Florida passport acceptance facilities accept walk-ins and which need appointments, with source conflicts flagged.",crumb="Walk-in vs appointment",long_page=True)
fb=f'''<h1>U.S. passport fees, forms and documents</h1><p>All amounts as stated by travel.state.gov on {D}.</p>
<h2>Which form</h2><div class="card"><ul><li><strong>DS-11 (in person)</strong>: first-time adults, children under 16, and adults whose passport was lost, stolen, damaged, issued over 15 years ago, or issued when under 16{src('adult','child')}.</li>
<li><strong>DS-82 (renew by mail)</strong>: you can submit your most recent passport, it was never reported lost or stolen, issued within the last 15 years, issued when you were 16 or older and valid for 10 years, in your current name (or you have a name change document), and not damaged beyond normal wear{src('renew')}.</li>
<li>Children's passports cannot be renewed; apply in person each time{src('child')}. <a href="/child-under-16/">Child under 16 in South Florida</a> covers consent, custody proof and minor fees.</li></ul></div>
<h2>Fees (DS-11, in person)</h2><div class="wrap" tabindex="0" aria-label="Fee table"><table><tr><th scope="col">Document</th><th scope="col">Adult 16+ application fee</th><th scope="col">Child under 16 application fee</th><th scope="col">Facility acceptance fee</th></tr>
<tr><td>Passport book</td><td>$130</td><td>$100</td><td>$35</td></tr><tr><td>Passport card</td><td>$30</td><td>$15</td><td>$35</td></tr><tr><td>Book and card</td><td>$160</td><td>$115</td><td>$35</td></tr></table></div><p class="src">Source: {src('fees')}</p>
<h2>Fees (DS-82 renewal by mail or online)</h2><div class="wrap" tabindex="0" aria-label="Renewal fee table"><table><tr><th scope="col">Document</th><th scope="col">Application fee</th></tr><tr><td>Passport book</td><td>$130</td></tr><tr><td>Passport card</td><td>$30</td></tr><tr><td>Book and card</td><td>$160</td></tr></table></div><p>No facility acceptance fee{src('fees','renew')}.</p>
<h2>Optional fees</h2><div class="card"><ul><li>Expedited service: $60 per application{src('fees')}.</li><li>1 to 3 day return delivery: $26.87 (not offered for card-only applications){src('fees')}.</li><li>File search if you cannot get evidence of citizenship: $150 when the missing passport or Consular Report of Birth Abroad was issued before 1994. If that record was issued in 1994 or later, do not pay the $150 when you apply. The State Department may ask for the $150 later if an electronic search does not find the record{src('fees','citizenship')}.</li><li>Faster shipping of your application to the State Department: paid to the acceptance facility; cost varies by location{src('fees')}.</li></ul></div>
<h2>How to pay at an acceptance facility</h2><div class="card"><p>Application fee: check (personal, certified, cashier's, traveler's) or money order payable to "U.S. Department of State", with the applicant's name and date of birth in the memo{src('fees')}. The $35 acceptance fee is paid to the facility; ask the facility what it accepts{src('fees')}. Example: Palm Beach Clerk accepts cash, a personal check, a cashier's check, a money order, MasterCard, Visa, American Express, or Discover for its $35 execution fee, and only a personal check, a cashier's check, or a money order for the State Department fee{src('pbcfees')}. Passport photos there are $16 each, and free for veterans, active-duty service members, and reservists who show a military discharge form (DD-214), military identification, or a veteran designation on a driver's license{src('pbc')}.</p></div>
<h2>Documents to bring (DS-11)</h2><div class="card"><ul><li>The DS-11, printed single-sided. Do not sign until the acceptance agent asks{src('adult')}.</li><li>Physical evidence of U.S. citizenship (for example a U.S. birth certificate, a full-validity undamaged passport, a Consular Report of Birth Abroad, or a Certificate of Naturalization or Citizenship) plus a photocopy. Digital or mobile birth certificates are not accepted{src('adult')}.</li>
<li>A physical photo ID such as a valid driver's license, plus a photocopy of front and back on 8.5 x 11 inch single-sided paper. If your ID is from another state, bring a second photo ID{src('adult')}.</li><li>One passport photo{src('adult','photos')}.</li>
<li>Children: proof of relationship, both parents' IDs, and if a parent cannot attend, Form DS-3053 notarized within 90 days, or other documents listed by the State Department{src('child')}. Full checklist: <a href="/child-under-16/">child under 16</a>.</li></ul></div>
<h2>Photo rules (summary)</h2><div class="card"><ul><li>1 color photo taken in the last 6 months, 2 x 2 inches (51 x 51 mm), head 1 to 1 3/8 inches (25 to 35 mm) chin to top of head{src('photos')}.</li><li>Plain white or off-white background, no shadows, no filters or edits{src('photos')}.</li><li>No glasses. Hats or head coverings only for documented religious or medical reasons, with a signed statement{src('photos')}.</li><li>No uniforms, camouflage or headphones; you may smile with mouth closed{src('photos')}.</li></ul></div>
<h2>Processing times (as officially stated)</h2><div class="card"><ul><li>Routine: 4 to 6 weeks. Expedited: 2 to 3 weeks{src('times')}.</li><li>Mailing is not included: up to 2 weeks to reach the State Department and up to 2 weeks to receive the passport{src('times')}.</li><li>Urgent travel needs an appointment at a passport agency and proof of international travel within 14 calendar days{src('times')}. The Miami Passport Agency is in a pilot that allows an appointment within 21 calendar days of travel, or within 28 calendar days if you need a foreign visa{src('miami')}. <a href="/urgent-travel/">How to book at the Miami Passport Agency</a>. Busiest season is late winter to summer; October to December is quieter{src('times')}.</li></ul></div>{MIAMI}'''
page('fees-and-documents/index.html',"Passport fees, DS-11 vs DS-82, documents and photo rules",fb,"Official U.S. passport fees, which form to use, documents, photo rules and processing times published on travel.state.gov.",crumb="Fees and documents",long_page=True)
URGENT=f'''<h1>Urgent travel at the Miami Passport Agency</h1>
<p>The Miami Passport Agency is the U.S. Department of State office for urgent passport appointments in South Florida. It is not a post office, clerk, or library acceptance facility. You need an appointment. A routine application goes to an acceptance facility in <a href="/counties/miami-dade/">Miami-Dade</a>, <a href="/counties/broward/">Broward</a>, or <a href="/counties/palm-beach/">Palm Beach</a>.{src('where','miami')}</p>
<p>Agency rules on this page were checked on 28 October 2026. Facility hours on the rest of this site were checked on 26 October 2026.</p>
<div class="card note"><strong>Official pages do not agree on the travel window.</strong><p>The Miami agency page lets you book for international travel within 21 calendar days, or within 28 calendar days if you need a foreign visa. The national appointment page, the processing-time page, the fees page, and the "where to apply" page still say 14 calendar days, or 28 if you need a foreign visa. The last section lists every conflict found on this check. When you book Miami, use the Miami page, and read the other page before you rely on a rule that conflicts.{src('miami','agency','times_en','fees','where')}</p></div>
<h2>The office</h2>
<div class="card"><p>Omni Center, 1501 Biscayne Blvd, Suite 400, Miami, FL 33132. {directions_html(AGENCY_ADDRESS, 'the Miami Passport Agency')}</p>
<p>Monday to Friday, 7:00 a.m. to 2:00 p.m. Closed Saturday, Sunday, and federal holidays. By appointment only.{src('miami')}</p>
<p>Appointments are free. A request to pay for an appointment is a fraud warning on the State Department page. The Department says it is not affiliated with third-party booking services, it may not honor an appointment booked that way, and you should not book a duplicate appointment.{src('miami','agency')}</p>
<p>The July 31, 2025 Miami page lists a mailing address in Sterling, Virginia: U.S. Department of State, Miami Passport Agency, CA/PPT/MM, 44132 Mercure Cir., PO Box 1094, Sterling, VA 20166-1094. That is not the office you visit. The current Miami page does not repeat this mailing address. Confirm it on that older page before you mail anything there.{src('miami_old','miami')}</p></div>
<h2>Which time limit applies to you</h2>
<div class="card"><ul>
<li>Miami's own page: an appointment for urgent international travel within 21 calendar days, or if you need a foreign visa within 28 calendar days.{src('miami')}</li>
<li>The same page says Detroit, Miami, and San Juan are in a pilot that allows an appointment within 21 calendar days of urgent travel. You can book online or by phone. The Department says it will use the pilot to gather data for its operations.{src('miami')}</li>
<li>The national "make an appointment" page: urgent travel abroad in the next 14 days, or a foreign visa in the next 28 days.{src('agency')}</li>
<li>The "where to apply" page: agencies help customers with urgent international travel within 14 calendar days, or a foreign visa within 28 calendar days. They require an appointment, proof of travel such as an airline ticket or hotel reservation, and an extra $60 expedited fee.{src('where')}</li>
<li>The processing-time page, last updated October 5, 2026: routine service is 4 to 6 weeks, expedited service is 2 to 3 weeks, and urgent travel requires an appointment plus proof of international travel within 14 calendar days. Mailing is extra: up to 2 weeks for the application to arrive, and up to 2 weeks to receive the passport.{src('times_en')}</li>
<li>The "get your passport fast" page, last updated September 30, 2026, splits the choice this way. Routine: you travel more than 6 weeks after you apply (4 to 6 weeks to process, and mailing may add 2 weeks). Expedited: you travel in less than 6 weeks ($60, 2 to 3 weeks to process, and mailing may add 2 weeks), at an acceptance facility or by mail if you are renewing. Urgent: you travel in less than 2 to 3 weeks, and you book an agency when you are within 14 calendar days of travel, or 28 days if you need a foreign visa. Life-or-death: travel in less than 14 days for the family emergency described below. You must have an appointment for urgent and life-or-death service, and a slot may not be free right away.{src('fast')}</li>
</ul>
<p>If your trip is outside the agency window, use expedited or routine service at an acceptance facility, or renew by mail or online if you qualify. Fee amounts, Form DS-11 (the in-person application), and Form DS-82 (the mail renewal) are on the <a href="/fees-and-documents/">fees and documents</a> page. Offices are on the <a href="/walk-in-vs-appointment/">walk-in or appointment</a> page.</p></div>
<h2>Life-or-death emergency</h2>
<div class="card"><p>You may qualify if you need to travel abroad in the next 2 weeks because an immediate family member outside the United States has died, is dying or in hospice care, or has a life-threatening illness or injury. The "get your passport fast" page describes the same service as travel in the next 14 days.{src('life','fast')}</p>
<p>An immediate family member is a parent or legal guardian, a child, a spouse, a sibling, or a grandparent. The page says aunts, uncles, cousins, and other relatives are not immediate family.{src('life')}</p>
<p>Travel for your own medical care does not qualify for life-or-death service. That page tells you to book a regular urgent appointment instead, and it says to do that when you are within 14 calendar days of travel. The Miami page's 21-day pilot is the conflict in the last section.{src('life','miami')}</p>
<p>Schedule the appointment up to 2 weeks before the trip. Gather these items first:{src('life')}</p>
<ul>
<li>Proof of the emergency: a death certificate, a statement from a mortuary, or a letter from the hospital. The hospital letter must be on hospital letterhead, signed by a doctor, and must explain the relative's medical condition.</li>
<li>A professional translation if that document is not in English.</li>
<li>Proof you are traveling abroad in the next 2 weeks, such as an itinerary or an airline ticket.</li>
<li>A passport application. The form depends on whether this is a new passport or a renewal. A passport photo. A valid government-issued photo identification (ID).</li>
</ul>
<p>If you have not applied yet, try the online appointment system first. If you cannot get an appointment online, or you have already applied, call. The current life-or-death page gives these hours:{src('life')}</p>
<ul>
<li>Monday to Friday, 8:00 a.m. to 5:00 p.m. Eastern Time (ET): 877-487-2778. If you are deaf or hard of hearing, call 888-874-7793 for telecommunications device for the deaf / teletypewriter (TDD/TTY) service.</li>
<li>Saturday, Sunday, federal holidays, and after 5:00 p.m. ET on weekdays: 202-647-4000. The page says not to call 202-647-4000 on weekdays from 8:00 a.m. to 5:00 p.m. ET.</li>
</ul>
<p>An older life-or-death page, last updated April 17, 2024, still gives different hours: 877-487-2778 until 8:00 p.m. ET on weekdays, and 202-647-4000 only after 8:00 p.m., on weekends, and on federal holidays. That older page also says not to call 202-647-4000 if you need urgent travel service rather than a life-or-death appointment. Use 877-487-2778 for an ordinary urgent trip.{src('life_old')}</p></div>
<h2>Book online if you have not applied</h2>
<div class="card"><p>The Miami page and the national appointment page give the same online steps. The system is the Online Passport Appointment System linked from those pages. This guide does not repeat a separate web address for it.{src('miami','agency')}</p>
<ol>
<li>Open the Online Passport Appointment System from the Miami agency page.</li>
<li>Enter the travel information. The system tells you whether you qualify. You can make an appointment for up to 7 people in your household.</li>
<li>Enter your email address. They email a code. Enter the code. Check the junk or spam folder if it is not in the inbox.</li>
<li>Enter your mobile phone number. They text another code. Enter that code.</li>
<li>Choose the date and time.</li>
<li>They email a confirmation. The system holds the appointment for 15 minutes. If you do not confirm within 15 minutes, start over.</li>
<li>To cancel or change an appointment you made online, use the link in the confirmation email.</li>
</ol>
<p>The pilot sentence says you may book online or by phone. The step list for people who have not yet applied only walks through the online system. The phone steps on the current page are for people who have already applied.{src('miami')}</p></div>
<h2>If you already applied</h2>
<div class="card"><p>The current Miami page says to call. If there is time to issue the passport before you travel, the Department notifies the office already working on the application. If there is not time, they make an appointment for you.{src('miami')}</p>
<ol>
<li>Call 877-487-2778. The current Miami page says Monday to Friday, 8:00 a.m. to 10:00 p.m. ET, and Saturday and Sunday, 10:00 a.m. to 3:00 p.m. ET. Spanish is offered ("Se habla español").{src('miami')}</li>
<li>If you are deaf or hard of hearing, call 888-874-7793 (TDD/TTY).{src('miami')}</li>
<li>If you qualify, they give you details they will check on the appointment day. If you are not the appointment holder, the agency will not see you.{src('miami')}</li>
<li>To cancel or change this appointment, the current page says to call. They give the slot to someone else. You cannot transfer it to another person.{src('miami')}</li>
</ol>
<p>Have the 9-digit application locator number. The first 2 digits say which agency or center has the file. You can look up the number on the application status page.{src('miami','times_en')} <a href="{S['status']}" rel="noopener">Check application status</a>.</p>
<p>The July 31, 2025 Miami page says Miami application numbers start with 51. The current page does not repeat that prefix. The same older page says the appointment phone line closes on federal holidays. The current phone steps do not say that. The older page also says that if you made the appointment by phone, you cancel by forwarding the confirmation email to NPIC@state.gov with the subject line "Cancel my Appointment." The current page says to call. Those cancel instructions conflict.{src('miami_old','miami')}</p></div>
<h2>What to bring</h2>
<div class="card"><p>The Miami page says the agency accepts all forms for first-time customers and for renewal customers. If you are not sure which form, it points you to the Department's passport fee and form calculator. Fill the form out online and print it. For Form DS-11, the adult application page says to print on one side of the paper only, and to sign only when the agent asks.{src('miami','adults_en')}</p>
<p>You must bring:{src('miami')}</p>
<ul>
<li>A printed confirmation of the appointment.</li>
<li>Printed proof of international travel. If you are flying, a flight receipt or an itinerary. If you are driving or taking a boat to Canada, Mexico, Bermuda, or the Caribbean, a hotel reservation, cruise or bus tickets, or international car insurance.</li>
<li>The application, and every supporting document that form requires. That includes the original citizenship evidence and a photocopy, and the original photo ID and a photocopy.</li>
<li>A passport photo. Size and background rules are on the <a href="/fees-and-documents/">fees and documents</a> page.</li>
<li>The application fee and the expedite fee. At the agency, pay by credit card, by debit card (the Miami page says not an automated teller machine, or ATM, card), or by a contactless payment such as Apple Pay, Google Pay, or Samsung Pay.</li>
</ul>
<p>A cruise from South Florida to the Bahamas or the Caribbean is in the boat category above: the named documents are a cruise ticket, a hotel reservation, or international car insurance, and the page says to bring them printed. A flight uses the flight receipt or itinerary, not the hotel-only list.{src('miami')}</p>
<p>The fees page adds card brands for an agency payment: Visa, Mastercard, American Express, and Discover for a credit card. For a debit card, or a prepaid card that is not linked to a line of credit or a bank account, it lists Visa or Mastercard. It says the agency will not accept any other form of payment. The Miami page does not name the brands, and it says "debit card (not ATM cards)" rather than the prepaid-card limit. Bring a card that satisfies both descriptions.{src('fees_en','fees','miami')}</p>
<p>Which form, and the document list for a first passport or a renewal, is on the <a href="/fees-and-documents/">fees and documents</a> page. If the passport was lost or stolen, you cannot use Form DS-82. The mail-renewal rules require that the passport was never reported lost or stolen, and the adult application page puts a lost, stolen, or damaged passport on Form DS-11, in person.{src('renew','adults_en')}</p></div>
<h2>Who must come</h2>
<div class="card"><ul>
<li>For a child under 16, the Miami page says both parents or guardians and the child must come to the appointment.{src('miami')}</li>
<li>The child passport page allows one parent to apply with Form DS-3053 (Statement of Consent) when the other parent still has custody but cannot attend. The Miami appointment page does not mention that form. Bring both parents if you can. Read <a href="/child-under-16/">the child page</a> before you rely on a consent form at the agency.{src('under16','miami')}</li>
<li>You may bring someone to help you apply, such as an attorney, an interpreter, or a family member.{src('miami')}</li>
<li>You may bring your service animal.{src('miami')}</li>
<li>You must be the appointment holder. The agency will not see someone else in your place, and you cannot transfer the appointment.{src('miami')}</li>
</ul></div>
<h2>The $60 expedite is a different service</h2>
<p>Paying $60 at a post office, clerk, or library does not give you a Miami agency appointment. The prices below are the application fees on the fees page, plus the $60 expedite.{src('fees','fast')}</p>
<div class="wrap" tabindex="0" aria-label="Acceptance facility expedite compared with a Miami agency appointment"><table>
<tr><th scope="col">Question</th><th scope="col">$60 expedite at an acceptance facility</th><th scope="col">Miami Passport Agency appointment</th></tr>
<tr><th scope="row">When the State Department points you here</th><td>Travel in less than 6 weeks, and not so soon that the fast page tells you to use an agency (less than 2 to 3 weeks, and within 14 calendar days on the national pages).</td><td>Miami page: travel within 21 calendar days, or a foreign visa needed within 28 calendar days. National pages: travel within 14 calendar days, or a visa within 28.</td></tr>
<tr><th scope="row">Appointment</th><td>Ask that office. Many South Florida offices require their own appointment. It is not an agency appointment.</td><td>Required. The agency does not take walk-ins.</td></tr>
<tr><th scope="row">Proof of travel</th><td>The acceptance-facility expedite steps do not ask for proof of travel.</td><td>Printed proof, in the categories above.</td></tr>
<tr><th scope="row">Adult application fee (age 16 and older)</th><td>Passport book $130, passport card $30, or both $160.</td><td>Same application fee, paid at the agency with the expedite fee.</td></tr>
<tr><th scope="row">Child under 16 application fee</th><td>Passport book $100, passport card $15, or both $115.</td><td>Same application fee, paid at the agency with the expedite fee.</td></tr>
<tr><th scope="row">Extra $60</th><td>Yes. Add it to the payment to the U.S. Department of State.</td><td>Yes. The Miami page calls it the expedite fee. The fees page lists "expedited at agency" as $60 and still states the 14-day travel limit.</td></tr>
<tr><th scope="row">$35 acceptance fee</th><td>Paid to the facility, on top of the State Department fees.</td><td>The Miami what-to-bring list does not mention it. See the conflict section.</td></tr>
<tr><th scope="row">How fast</th><td>2 to 3 weeks after the Department has the application, then mailing (up to 2 weeks each way).</td><td>No published number of days. At the window, staff discuss options based on your travel date.</td></tr>
</table></div>
<p class="src">Sources for this table: {src('fees','fees_en','fast','times_en','miami','where')}</p>
<h2>On the day of the appointment</h2>
<div class="card"><ol>
<li>Arrive 15 minutes early for security screening.{src('miami')}</li>
<li>Do not bring weapons or sharp objects.{src('miami')}</li>
<li>Do not bring food or drinks, except water in a sealable bottle.{src('miami')}</li>
<li>Use the first floor of the Omni Building's northeast (NE) 15th Street entrance, then take the elevator to the fourth floor.{src('miami')}</li>
<li>Check in at the information window and give your appointment confirmation number.{src('miami')}</li>
<li>Wait in the lobby until they call your number. They might not call you at the exact appointment time.{src('miami')}</li>
<li>Go to the window they assign. Staff review the application and supporting documents, then discuss how you will get the passport. They decide that from your travel date.{src('miami')}</li>
</ol>
<p>The July 31, 2025 Miami page says to print the Department's social story before you go. It describes the visit and may help a customer on the autism spectrum. The current day-of list does not repeat that line. The link, if it is still posted, is on the older page.{src('miami_old')}</p></div>
<h2>Where the official pages disagree</h2>
<div class="card note"><p>Checked 28 October 2026. These are disagreements between travel.state.gov pages. This site does not choose one. For a Miami booking, start with the current Miami page.</p>
<ol>
<li><strong>14 calendar days or 21.</strong> The current Miami page, including its pilot note, says 21 calendar days for urgent travel, or 28 calendar days if you need a foreign visa. The national appointment page, the processing-time page (last updated October 5, 2026), the "get your passport fast" page (last updated September 30, 2026), the "where to apply" page, the fees page's "expedited at agency" line, and the mail-renewal page still say 14 calendar days (28 for a visa, on the pages that mention a visa). The July 31, 2025 Miami page also still says 14 calendar days. The life-or-death page sends people traveling for their own medical care to the 14-day urgent rule. Two of those pages also use a longer phrase next to the 14-day rule: the fast page says urgent travel is "less than 2-3 weeks," and the mail-renewal page says to make an appointment if you travel in less than 3 weeks, then says the appointment must be within 14 calendar days.{src('miami','miami_old','agency','times_en','fast','where','fees','life','renew_en')}</li>
<li><strong>Life-or-death phone hours.</strong> The current life-or-death page uses 877-487-2778 until 5:00 p.m. ET on weekdays, then 202-647-4000. The April 17, 2024 life-or-death page uses 877-487-2778 until 8:00 p.m. ET, then 202-647-4000, and it says not to use 202-647-4000 for urgent travel service.{src('life','life_old')}</li>
<li><strong>How to cancel an appointment made by phone.</strong> The current Miami page says to call. The July 31, 2025 Miami page says to email NPIC@state.gov with the subject "Cancel my Appointment."{src('miami','miami_old')}</li>
<li><strong>The $35 acceptance fee at the agency.</strong> For Form DS-11 at an acceptance facility, the fees page lists a $35 fee paid to the facility, on top of the application fee. The Miami what-to-bring list names the application fee and the expedite fee, and it does not name a $35 fee. The fee calculator on the fees page still includes a $35 execution-fee line. It is not clear from that page whether the line remains when the service is expedited at an agency. Ask for the total at the window before you pay.{src('fees','fees_en','miami')}</li>
<li><strong>One parent for a child under 16.</strong> The Miami page says both parents or guardians and the child come to the appointment. The child passport page allows Form DS-3053 when one parent cannot attend. The agency page does not mention that exception.{src('miami','under16')}</li>
</ol></div>
<h2>Sources</h2>
<ul>
<li><a href="{S['miami']}" rel="noopener">Miami Passport Agency</a>. Current page: 21-day pilot, hours, online and phone booking, what to bring, who attends, and the Omni Center entrance.</li>
<li><a href="{S['miami_old']}" rel="noopener">Apply at the Miami Passport Agency</a>. Older page, last updated July 31, 2025: 14-day rule, Sterling mailing address, application numbers starting with 51, phone holiday closure, email cancellation, and the social story.</li>
<li><a href="{S['agency']}" rel="noopener">Make an Appointment at a Passport Agency</a>. National rule of 14 days, or 28 days for a visa, and the same online steps.</li>
<li><a href="{S['life']}" rel="noopener">Get a Passport If You Have a Life-or-Death Emergency</a>. Current emergency rules and the 5:00 p.m. phone split.</li>
<li><a href="{S['life_old']}" rel="noopener">Life-or-Death Emergencies</a>. Older page, last updated April 17, 2024: 8:00 p.m. phone split, and the warning not to use 202-647-4000 for urgent travel service.</li>
<li><a href="{S['fast']}" rel="noopener">Get Your Passport Fast</a>. Last updated September 30, 2026. Routine, expedited, urgent, and life-or-death choices.</li>
<li><a href="{S['times_en']}" rel="noopener">Get Your Processing Time</a>. Last updated October 5, 2026. Routine 4 to 6 weeks, expedited 2 to 3 weeks, urgent travel within 14 calendar days.</li>
<li><a href="{S['where']}" rel="noopener">Where to Apply for a U.S. Passport</a>. Agencies versus acceptance facilities.</li>
<li><a href="{S['fees']}" rel="noopener">Passport Fees</a>. Application fees, the $60 expedite, the $35 acceptance fee, the 14-day limit on expedited service at an agency, and agency card payment.</li>
<li><a href="{S['fees_en']}" rel="noopener">Passport Fees</a> (the newer fees address). Card brands accepted at an agency, and the statement that no other payment is accepted.</li>
<li><a href="{S['adults_en']}" rel="noopener">Apply for Your Adult Passport</a>. Print Form DS-11 on one side, sign when the agent asks, and apply in person if the passport was lost, stolen, or damaged.</li>
<li><a href="{S['renew_en']}" rel="noopener">Renew Your Passport by Mail</a>. Form DS-82 is not available if the passport was reported lost or stolen. This page also says to book an appointment within 14 calendar days if you travel in less than 3 weeks.</li>
<li><a href="{S['under16']}" rel="noopener">Apply for a Child's Passport Under 16</a>. Form DS-3053 when one parent cannot attend.</li>
<li><a href="{S['status']}" rel="noopener">Passport application status</a>. Where the processing-time page sends you to look up a locator number.</li>
</ul>
<p>On this site: <a href="/fees-and-documents/">fees and documents</a>, <a href="/child-under-16/">a child under 16</a>, and <a href="/counties/miami-dade/">Miami-Dade acceptance facilities</a>.</p>'''
page('urgent-travel/index.html',"Miami Passport Agency appointments for urgent travel",URGENT,"How to book the Miami Passport Agency for urgent travel or a life-or-death emergency, including proof of travel, fees, and how the $60 expedite differs.",checked="28 October 2026",crumb="Urgent travel",long_page=True)
faq=[("Can I walk in at a post office?",f"USPS listings in the locator point to usps.com/scheduler for appointments and additional times{src('usps','pafl')}. Some USPS hours in the data are flagged walk-in. See the <a href=\"/walk-in-vs-appointment/\">walk-in page</a>."),
("Which South Florida offices say they take walk-ins?",f"Broward Clerk of Courts lists passport hours at its Central, North, South and West courthouses{src('broward')}, and the locator comments for its regional courthouses say appointments are not required{src('pafl')}. Palm Beach Clerk says walk-in customers are not accepted{src('pbc')}. Miami-Dade Public Library says its passport service is by appointment only{src('mdpls')}."),
("How much does a first adult passport book cost?",f"$130 to the U.S. Department of State plus $35 to the acceptance facility{src('fees')}."),
("Can I renew at an acceptance facility?",f"If you are eligible for DS-82, you renew by mail or online. Postal employees should not charge the $35 fee or review a DS-82{src('renew')}."),
("I travel in less than two weeks. Where do I go?",f"Most passport agencies take an appointment once you are within 14 calendar days of international travel, or within 28 calendar days if you need a foreign visa. The Miami Passport Agency is in a pilot that allows an appointment within 21 calendar days of urgent travel, or within 28 calendar days if you need a foreign visa. Call 877-487-2778. <a href=\"/urgent-travel/\">Miami agency appointments, proof of travel, and life-or-death rules</a>.{src('miami','times')}."),
("Do I need both parents for a child's passport?",f"For a child under 16, both parents or guardians must be present or give approval, for example with a notarized DS-3053. Sole custody uses different documents, and ages 16 and 17 follow another rule. <a href=\"/child-under-16/\">Child under 16</a>.{src('under16','teen')}"),
("Can I bring a digital birth certificate?",f"No. Physical evidence of citizenship only{src('adult')}."),
("Do facilities take photos?",f"Some do; the locator flags 'photos on site'{src('pafl')}. Palm Beach Clerk sells photos for $16 each, and that photo is free for veterans, active-duty service members, and reservists who show military identification or a discharge form{src('pbc')}. Miami-Dade libraries say photo service is not currently available{src('mdpls')}.")]
page('faq/index.html',"South Florida passport FAQ: walk-ins, fees, documents",'<h1>Passport FAQ for South Florida</h1>'+''.join(f'<h2>{q}</h2><div class="card"><p>{a}</p></div>' for q,a in faq),"Short sourced answers on walk-in hours, fees, documents and applying for a U.S. passport in Miami-Dade, Broward and Palm Beach.",crumb="FAQ",faq_items=faq,long_page=True)
CHILD=f'''<h1>Passport for a child under 16 in South Florida</h1>
<p>A child under 16 applies in person with Form DS-11 at a passport acceptance facility. Bring the child. You cannot renew a child's passport, and the passport is valid for 5 years. Both parents or guardians go with the child, or you bring the consent or custody documents below.{src('under16')}</p>
<div class="card note"><strong>Ages 16 and 17 use different rules.</strong> They still apply in person on DS-11, but only one parent or guardian has to show they know about the application, the passport is valid for 10 years, and the fees are the adult fees. Those rules are at the end of this page.{src('teen')}</div>
<h2>Where to apply in Miami-Dade, Broward and Palm Beach</h2>
<p>Use an acceptance facility (post office, clerk of court, or library) if international travel is more than 3 weeks away, and ask whether that office needs an appointment. If the child is traveling internationally in less than 3 weeks, make an appointment at a passport agency once you are within 14 calendar days of travel.{src('under16')} The Miami Passport Agency is in a pilot that allows an appointment within 21 calendar days of urgent travel, or within 28 calendar days if you need a foreign visa.{src('miami')} <a href="/urgent-travel/">Booking steps, proof of travel, and the life-or-death rule</a>. Facilities: <a href="/counties/miami-dade/">Miami-Dade</a>, <a href="/counties/broward/">Broward</a>, <a href="/counties/palm-beach/">Palm Beach</a>.</p>
<div class="card"><strong>Miami-Dade Public Library</strong><p>North Dade Regional, West Kendall Regional and Naranja Branch take applications by appointment only. Book a separate appointment for each person, including each child. A family of five needs five appointments. These libraries do not take passport photos, so bring the photo. The library's execution fee is $35 per application, paid in cash, by cashier's check, or by money order payable to "Miami-Dade Public Library System." The State Department fee is a check or money order only.{src('mdpls')}</p>
<p>On the library's own list, applicants age 15 or under who submit a naturalization certificate or a Certificate of Citizenship must also include a certified birth certificate.{src('mdpls')}</p></div>
<div class="card"><strong>Broward Clerk of Courts</strong><p>The child must appear. The clerk's office says both parents must appear if both are listed on the birth certificate. If one cannot, bring Form DS-3053 and a copy of that parent's identification, front and back. If a parent is not listed on the legal birth certificate, the clerk's office says only the listed parents must appear or give consent in writing.{src('broward')}</p>
<p>Pay the State Department fees (application, expedite, and 1 to 3 day delivery) by personal check, cashier's check, or money order to "U.S. Department of State." The clerk says each applicant needs a separate money order, and that a check or money order must be for the exact amount. The clerk's own fees are $35 to execute the application, $15 for a photo, and $1 per page for copies, paid in cash or by American Express, Discover, MasterCard, or Visa.{src('broward')}</p></div>
<h2>Form DS-11</h2>
<div class="card"><ul>
<li>Use Form DS-11. Complete it in the State Department form filler and print it. Download the PDF if the form filler fails.{src('under16','forms')}</li>
<li>Print single-sided, on 8.5 by 11 inch paper, in vertical portrait format, with the form filling the page. Double-sided or horizontal printouts are not accepted.{src('forms','under16')}</li>
<li>Do not sign until the acceptance agent asks. The agent checks identification, gives an oath, and then has you sign the child's application.{src('under16')}</li>
<li>If you use the form filler, the only handwriting on the form should be the original signature and the date.{src('forms')}</li>
<li>Broward Clerk tells applicants to complete DS-11 in black ink only, with no white-out.{src('broward')}</li>
<li>Do not staple the photo. The agent reviews it and staples it.{src('under16')}</li>
<li>You can request a passport book, a passport card, or both. If the child travels internationally several times a year, check the large book box for extra visa pages.{src('under16')}</li>
</ul></div>
<h2>Both parents or guardians</h2>
<div class="card"><p>Both parents or guardians must be present with the child, unless you have the documents in the next sections. Each parent or guardian who appears brings a physical photo ID. The usual ID is a fully valid driver's license or enhanced driver's license. If the ID is from a different state than the one where you are applying, bring a second photo ID. Photocopy the front and back of each parent's or guardian's ID on one side of 8.5 by 11 inch paper.{src('under16')}</p></div>
<h2>One parent cannot attend, and both still have custody</h2>
<div class="card"><p>The parent who cannot come signs and dates Form DS-3053, Statement of Consent, in front of a certified notary. Submit that form with the DS-11, plus a photocopy of the photo ID shown to the notary. DS-3053 and other notarized statements must be submitted within 90 days after they are signed or notarized.{src('under16','forms')}</p>
<ul>
<li>An electronically notarized statement is accepted if state law allows that notarization. Bring a printed copy.{src('under16')}</li>
<li>If that parent is outside the United States, some countries require DS-3053 to be notarized at a U.S. embassy or consulate, not by a local notary. The State Department list currently includes Haiti, the Dominican Republic, Jamaica, Venezuela, Honduras, Nicaragua, and others. Use the list on the child passport page before you rely on a local notary.{src('under16')}</li>
</ul></div>
<h2>Sole custody, or you are the only parent</h2>
<div class="card"><p>Provide one of these documents:{src('under16')}</p>
<ul>
<li>A court order granting you sole custody, or giving only you permission to apply for the child's passport.</li>
<li>A certified copy of the child's birth certificate or adoption decree that lists you as the only parent or guardian.</li>
<li>A certified copy of the death certificate of the parent or guardian who cannot appear.</li>
<li>A certified copy of a judicial declaration of incompetence of the parent who cannot appear.</li>
</ul></div>
<h2>Foster care or a pending adoption</h2>
<div class="card"><p>If the child is pending adoption or in foster care, and a state children services office, a private institution, or an individual is the legal guardian, bring all of the following:{src('under16')}</p>
<ul>
<li>A certified copy of the court order naming that office, institution, or individual as the child's legal guardian. The order must say there are no restrictions on issuing a U.S. passport, and it must still be valid, with no pending or upcoming action.</li>
<li>A letter on official letterhead from the office, institution, or guardian that lets the person applying with the child sign on their behalf, plus a completed Form DS-3053.</li>
<li>The employee ID of the person who wrote the letter, and the employee ID of the person applying with the child, to show both work for that office or institution.</li>
</ul></div>
<h2>You cannot find the other parent</h2>
<div class="card"><p>If both parents or guardians still have custody and you cannot locate the other one, submit Form DS-5525, Statement of Special Family Circumstances, with the DS-11. The State Department may ask for more evidence, such as a custody order, an incarceration order, or a restraining order to protect against international parental child abduction. If the other parent is deployed with the military, that parent should provide a notarized DS-3053 in most cases.{src('under16','forms')}</p></div>
<h2>Neither parent can appear</h2>
<div class="card"><p>The adult who brings the child (for example a grandparent) must show permission: Form DS-3053, or a notarized statement from both parents, submitted within 90 days after notarization, plus a photocopy of both parents' or guardians' photo IDs. If the statement is from only one parent or guardian, also show that parent or guardian has sole custody.{src('under16')}</p></div>
<h2>Citizenship evidence</h2>
<div class="card"><p>Bring one primary citizenship document on paper, plus a photocopy of the front. Copy the back as well if it has printing. Use white 8.5 by 11 inch paper, one side only. Digital or mobile birth certificates are not accepted. Bring the original, or a replacement that has the seal or stamp of the office that issued it. You may also submit a second certified copy, which the State Department keeps. Leaving out the photocopy can slow the application.{src('under16','citizenship')}</p>
<p>The child application page lists these primary documents:{src('under16')}</p>
<ul>
<li>A U.S. birth certificate.</li>
<li>A Consular Report of Birth Abroad, or another birth document issued by the U.S. Department of State.</li>
<li>A Certificate of Citizenship.</li>
<li>A full validity, undamaged U.S. passport. For a child under 16, full validity means the passport is or was valid for 5 years.</li>
</ul>
<p>A U.S. birth certificate must show the child's full name, date of birth, and place of birth; the parents' full names; the city, county, or state of birth; the registrar's signature; the date it was filed with the registrar, which must be within 1 year of birth; and the seal or stamp of the office that issued it.{src('citizenship')}</p>
<p>If the child was born outside the United States, a Certificate of Naturalization is also primary evidence.{src('citizenship')}</p>
<p>Child born abroad who got U.S. citizenship at birth through a U.S. citizen parent: submit the foreign birth certificate listing the parent or parents, evidence of that parent's U.S. citizenship, the parents' marriage certificate if they were married, and a statement of when and where the parents lived in the United States and abroad before the birth.{src('citizenship')}</p>
<p>Citizenship through a parent's naturalization, or through the Child Citizenship Act of 2000, uses a separate list on that same page: the foreign birth certificate, the parent's U.S. citizenship evidence, proof of the child's permanent residence, legal-custody documents, and proof the child lived in the United States with the U.S. citizen parent. Follow that list rather than the birth-certificate list above.{src('citizenship')}</p>
<p>A document in a foreign language needs a professional English translation. The translator must provide a notarized letter about the accuracy of the translation and their ability to translate.{src('citizenship')}</p>
<p>If you cannot get primary evidence, the citizenship page explains secondary evidence: a delayed birth certificate or a letter of no record, plus early public records.{src('citizenship')}</p></div>
<h2>Proof of the parental relationship</h2>
<div class="card"><p>The State Department must see the legal relationship between the child and each parent or guardian. A U.S. birth certificate that proves citizenship and names the parents does both jobs. If you do not have that, submit a document that shows who the parents or legal guardians are. Examples the State Department gives: a foreign birth certificate, an adoption decree, a divorce or custody decree, or a court order.{src('under16')}</p>
<p>If your name now is different from the name on that document, bring proof of the legal name change, such as a name change decree or a marriage certificate.{src('under16')}</p></div>
<h2>Fees for a child under 16</h2>
<p>You pay two fees: the application fee to the U.S. Department of State, and a $35 acceptance fee to the facility. Amounts below are the child-under-16 fees on travel.state.gov.{src('fees','under16')}</p>
<div class="wrap" tabindex="0" aria-label="Child fee table"><table><tr><th scope="col">Document</th><th scope="col">Form</th><th scope="col">Application fee</th><th scope="col">Facility acceptance fee</th></tr>
<tr><td>Passport book</td><td>DS-11</td><td>$100</td><td>$35</td></tr>
<tr><td>Passport card</td><td>DS-11</td><td>$15</td><td>$35</td></tr>
<tr><td>Book and card</td><td>DS-11</td><td>$115</td><td>$35</td></tr></table></div>
<div class="card"><ul>
<li>Pay the application fee by check (personal, certified, cashier's, or traveler's) or money order payable to "U.S. Department of State." Write the child's name and date of birth in the memo.{src('fees','under16')}</li>
<li>The State Department prefers a separate check or money order for each child. One check for a whole family is accepted if the memo lists each applicant's name and date of birth, and how many applications the check covers.{src('under16')}</li>
<li>At a Broward Clerk office, follow that office's rule: a separate money order for each applicant.{src('broward')}</li>
<li>Pay the $35 acceptance fee to the facility and ask what it takes. Miami-Dade libraries and the Broward Clerk publish their own methods in the sections above.{src('fees','mdpls','broward')}</li>
<li>Optional expedited service is $60 per application, added to the State Department payment.{src('fees')}</li>
<li>Optional 1 to 3 day delivery, after the State Department mails the new passport, is $26.87. It is not offered for a card-only application. Do not send a prepaid return envelope.{src('fees')}</li>
<li>You can pay the acceptance facility to ship the application faster by Priority Mail Express. That price depends on the location.{src('fees','under16')}</li>
<li>The application fee and the execution fee are not refunded, even if no passport is issued.{src('fees')}</li>
</ul>
<p>Routine service is 4 to 6 weeks. Expedited service is 2 to 3 weeks. Those times do not include mailing: up to 2 weeks for the application to reach the State Department, and up to 2 weeks to receive the passport.{src('under16')}</p>
<p>Supporting documents (the previous passport, birth certificate, or naturalization certificate) come back separately by First Class Mail, up to 4 weeks after the passport. If they have not arrived after 4 weeks, call 877-487-2778. To ask for reimbursement of a lost supporting document, contact the State Department within 120 days of the date it mailed the passport, and provide a receipt for the replacement cost.{src('under16')}</p></div>
<h2>The child's photo</h2>
<div class="card"><ul>
<li>One color photo taken in the last 6 months. Printed size 2 x 2 inches (51 x 51 mm), with the head 1 to 1 3/8 inches (25 to 35 mm) from chin to top of head. Do not attach it yourself.{src('under16','photohelp')}</li>
<li>Plain white or off-white background, no shadows, no filters or digital edits. No glasses. No uniform.{src('photohelp')}</li>
<li>For a baby or toddler, put the child on a plain white or off-white sheet, or cover a car seat with that sheet and sit the child in it. No other person in the photo. The child faces the camera, full face visible, neutral expression, no shadows on the face.{src('photohelp')}</li>
<li>A baby's eyes do not have to be entirely open. Every older child must have both eyes open.{src('photohelp')}</li>
<li>A photo is not accepted if a pacifier, hands, or anything else blocks part of the face.{src('photohelp')}</li>
</ul>
<p>Broward Clerk takes photos for $15. Miami-Dade library passport desks do not.{src('broward','mdpls')}</p></div>
<h2>Ages 16 and 17</h2>
<div class="card"><p>Do not use the under-16 consent rules for a 16 or 17 year old. That applicant uses DS-11 in person for a first adult passport. The passport is valid for 10 years. Show that one legal parent or guardian knows about the application, in any one of these ways:{src('teen')}</p>
<ul>
<li>The parent or guardian comes along, shows an acceptable photo ID, signs the DS-11, and you bring a photocopy of that ID.</li>
<li>You submit a signed note from the parent or guardian and a photocopy of their ID.</li>
<li>You list the parent or guardian in the emergency contact section of the application.</li>
<li>You pay with a check in the parent or guardian's name.</li>
</ul>
<p>If it is not clear that a parent knows, the State Department may ask for a notarized DS-3053 and a photocopy of that parent's ID. If the applicant is enrolled in the Children's Passport Issuance Alert Program, the State Department contacts the parent or guardian who enrolled them before it issues the passport.{src('teen')}</p>
<p>Fees at 16 and 17 are the adult DS-11 fees, not the under-16 fees: passport book $130, passport card $30, book and card $160, plus the $35 facility fee.{src('teen','fees')}</p></div>
<p>Related: <a href="/fees-and-documents/">fees and documents</a> and the <a href="/faq/">FAQ</a>.</p>'''
page('child-under-16/index.html',"U.S. passport for a child under 16 in South Florida",CHILD,"How to apply for a U.S. passport for a child under 16 in Miami-Dade, Broward and Palm Beach: DS-11, both parents, DS-3053, custody proof, documents and fees.",checked="26 October 2026",crumb="Child under 16",long_page=True)
GLYPHS={
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
'C':['01111','10000','10000','10000','10000','10000','01111'],
'D':['11110','10001','10001','10001','10001','10001','11110'],
'E':['11111','10000','10000','11110','10000','10000','11111'],
'F':['11111','10000','10000','11110','10000','10000','10000'],
'G':['01111','10000','10000','10111','10001','10001','01111'],
'H':['10001','10001','10001','11111','10001','10001','10001'],
'I':['01110','00100','00100','00100','00100','00100','01110'],
'J':['00111','00010','00010','00010','00010','10010','01100'],
'K':['10001','10010','10100','11000','10100','10010','10001'],
'L':['10000','10000','10000','10000','10000','10000','11111'],
'M':['10001','11011','10101','10101','10001','10001','10001'],
'N':['10001','11001','10101','10011','10001','10001','10001'],
'O':['01110','10001','10001','10001','10001','10001','01110'],
'P':['11110','10001','10001','11110','10000','10000','10000'],
'Q':['01110','10001','10001','10001','10101','10010','01101'],
'R':['11110','10001','10001','11110','10100','10010','10001'],
'S':['01111','10000','10000','01110','00001','00001','11110'],
'T':['11111','00100','00100','00100','00100','00100','00100'],
'U':['10001','10001','10001','10001','10001','10001','01110'],
'V':['10001','10001','10001','10001','10001','01010','00100'],
'W':['10001','10001','10001','10101','10101','10101','01010'],
'X':['10001','10001','01010','00100','01010','10001','10001'],
'Y':['10001','10001','01010','00100','00100','00100','00100'],
'Z':['11111','00001','00010','00100','01000','10000','11111'],
' ' :['00000','00000','00000','00000','00000','00000','00000'],
'-':['00000','00000','00000','11111','00000','00000','00000'],
',':['00000','00000','00000','00000','00110','00110','01100'],
}
NAVY=(0x1f,0x3a,0x68); CREAM=(0xf4,0xf7,0xfb); WHITE=(255,255,255); GOLD=(0xf3,0xd2,0x7a); MUTED=(0xdb,0xe4,0xf5)
def blank(w,h,color):
    px=bytes(color)
    return bytearray(px*(w*h)),w,h
def rect(buf,w,h,x,y,rw,rh,color):
    x0,y0,x1,y1=max(0,x),max(0,y),min(w,x+rw),min(h,y+rh)
    if x0>=x1 or y0>=y1: return
    span=bytes(color)*(x1-x0)
    for yy in range(y0,y1):
        i=(yy*w+x0)*3
        buf[i:i+len(span)]=span
def disc(buf,w,h,cx,cy,r,color):
    r2=r*r
    for yy in range(max(0,cy-r),min(h,cy+r+1)):
        for xx in range(max(0,cx-r),min(w,cx+r+1)):
            if (xx-cx)*(xx-cx)+(yy-cy)*(yy-cy)<=r2:
                i=(yy*w+xx)*3; buf[i:i+3]=bytes(color)
def text(buf,w,h,s,x,y,scale,color,gap=None):
    if gap is None: gap=scale
    for ch in s:
        g=GLYPHS[ch]
        for ry,row in enumerate(g):
            for rx,bit in enumerate(row):
                if bit=='1': rect(buf,w,h,x+rx*scale,y+ry*scale,scale,scale,color)
        x+=5*scale+gap
    return x
def passport(buf,w,h,x,y,s):
    rect(buf,w,h,x,y,s,int(s*1.38),CREAM)
    m=max(4,s//10)
    rect(buf,w,h,x+m,y+m,s-2*m,int(s*1.38)-2*m,NAVY)
    inset=max(3,s//16)
    rect(buf,w,h,x+m+inset,y+m+inset,s-2*m-2*inset,int(s*1.38)-2*m-2*inset,CREAM)
    cx,cy=x+s//2,y+int(s*0.50)
    disc(buf,w,h,cx,cy,int(s*0.16),NAVY)
    disc(buf,w,h,cx,cy,int(s*0.09),CREAM)
    lw=max(3,s//22)
    rect(buf,w,h,x+int(s*0.28),y+int(s*0.86),int(s*0.44),lw,NAVY)
    rect(buf,w,h,x+int(s*0.34),y+int(s*1.02),int(s*0.32),lw,NAVY)
def save_png(path,buf,w,h):
    raw=bytearray()
    for y in range(h):
        raw.append(0); raw.extend(buf[y*w*3:(y+1)*w*3])
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b'')
    open(path,'wb').write(png)
def write_assets():
    os.makedirs(OUT,exist_ok=True)
    w,h=1200,630
    buf,w,h=blank(w,h,NAVY)
    rect(buf,w,h,0,0,18,h,GOLD)
    passport(buf,w,h,86,145,230)
    text(buf,w,h,'SOUTH FLORIDA',390,185,8,WHITE)
    text(buf,w,h,'PASSPORT PLACES',390,285,8,WHITE)
    text(buf,w,h,'MIAMI-DADE, BROWARD AND PALM BEACH',360,420,4,MUTED)
    save_png(os.path.join(OUT,'og.png'),buf,w,h)
    aw=ah=180
    abuf,aw,ah=blank(aw,ah,NAVY)
    passport(abuf,aw,ah,46,28,88)
    save_png(os.path.join(OUT,'apple-touch-icon.png'),abuf,aw,ah)
    open(os.path.join(OUT,'favicon.svg'),'w').write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#1f3a68"/><rect x="8" y="5" width="16" height="22" rx="1.5" fill="#f4f7fb"/><circle cx="16" cy="13" r="3.1" fill="none" stroke="#1f3a68" stroke-width="1.5"/><rect x="11" y="19.5" width="10" height="1.5" rx="0.75" fill="#1f3a68"/><rect x="12.2" y="22.5" width="7.6" height="1.5" rx="0.75" fill="#1f3a68"/></svg>\n')
    shutil.copytree(os.path.join(HERE,'vendor','leaflet'), os.path.join(OUT,'vendor','leaflet'))
    shutil.copy(os.path.join(HERE,'map.js'), os.path.join(OUT,'map.js'))
DISC=f'''<h1>Disclaimer</h1>
<p>{H.escape(DISCLAIMER)}</p>
<h2>Accuracy</h2>
<p>Hours, fees, forms and document rules on this site are taken from the official pages linked on each guide, as of the last-checked date on that page. Those sources can change after that date. This site can be incomplete or wrong, including a missed facility, a misread hours flag, or a lag behind an operator's own page. Where the sources disagree, the page says so.</p>
<h2>No warranty</h2>
<p>This site is provided as is and as available. There is no warranty of any kind, express or implied, including of accuracy, completeness, timeliness, fitness for a particular purpose, or non-infringement.</p>
<h2>Limitation of liability</h2>
<p>To the fullest extent permitted by law, the operator of this site accepts no liability for any loss, cost, or damage that results from using this site or relying on it. That includes a missed appointment, a refused application, a fee, a delay, or a change in travel plans. You use this site at your own risk.</p>
<h2>External links are not endorsed</h2>
<p>Links to travel.state.gov, the Passport Acceptance Facility Locator, USPS, clerks of court, libraries, the Census Bureau, and other sites are there so you can read the source. A link is not an endorsement, and this site does not control those pages.</p>
<h2>Not affiliated</h2>
<p>This independent site is not affiliated with, endorsed by, or operated by the U.S. Department of State, USPS, any clerk of court, any library, or any other government agency. It does not sell or promote expediting services, and it does not submit applications.</p>
<h2>Check official sources</h2>
<p>Before you go to a facility or mail an application, confirm the hours, whether you need an appointment, the fees, and the documents on the official page linked from the guide, or by calling the facility.</p>
<h2>Contact and corrections</h2>
<p>This site does not offer passport services and has no contact form or email address. It cannot update an application with the U.S. Department of State. If something here disagrees with the official source linked on the page, follow the official source.</p>'''
page('disclaimer/index.html',"Disclaimer for this South Florida passport acceptance guide",DISC,"Accuracy, no warranty, limitation of liability, external links, affiliation, official sources and corrections for this passport guide.",checked="26 October 2026",crumb="Disclaimer",long_page=True)
find_body='<h1>All pages</h1><p>Type in the search box at the top of this page. The list below stays complete if search is not available.</p><p id="index-status" class="index-status" aria-live="polite">Showing every page.</p><h2>Pages by topic</h2><div id="page-index">'
find_body+='<section><h2>Home</h2><ul class="index-list"><li data-keywords="home start">'+jump('index.html')+'</li></ul></section>'
for g,items in GROUPS:
    find_body+=f'<section><h2>{esc(g)}</h2><ul class="index-list">'+''.join(
        f'<li data-keywords="{esc(site.aliases.get(p,""))}">{jump(p)}</li>' for p,_t in items)+'</ul></section>'
find_body+='</div>'
page('find/index.html',"Find every page in this South Florida passport guide",find_body,"Search or browse every page in this independent guide to South Florida passport acceptance facilities, walk-in hours, fees and documents.")
HUBS=[('/','Home'),('/counties/miami-dade/','Miami-Dade County'),('/counties/broward/','Broward County'),('/counties/palm-beach/','Palm Beach County'),('/walk-in-vs-appointment/','Walk-in vs appointment'),('/fees-and-documents/','Fees and documents'),('/urgent-travel/','Urgent travel'),('/child-under-16/','Child under 16'),('/faq/','FAQ'),('/find/','All pages')]
page('404.html',"Page not found: South Florida passport acceptance guide",'<h1>Page not found</h1><p>That address is not on this site. Use the navigation above or one of these guides:</p><ul>'+''.join(f'<li><a href="{h}">{n}</a></li>' for h,n in HUBS)+'</ul>',"That address is not on this site. Browse passport acceptance facilities in Miami-Dade, Broward and Palm Beach, plus fees, documents and walk-in hours.",crumb="Page not found",error=True)
write_assets()
site.finish()
pinned=sum(1 for r in recs if point_ok(COORD['places'].get(r['id'])))
print(len(recs),'facilities',{k:len(v) for k,v in cc.items()},'walk',nwalk,'conflicts',ncon,'pinned',pinned,'unplaced',len(recs)-pinned)
for r in recs:
    if not point_ok(COORD['places'].get(r['id'])):
        print(' UNPLACED:', r['id'], r['name'], '|', COORD.get('unplaced',{}).get(r['id'],{}).get('reason',''))
if not point_ok(COORD.get('miami_passport_agency')):
    raise SystemExit('Miami Passport Agency has no confident coordinate')
for r in recs:
    if r['conflict']: print(' C:',r['name'],'|',r['conflict'])
