#!/usr/bin/env python3
"""Build the South Florida passport acceptance facility site from JSON in tools/ into site/."""
import json,os,re,html as H,shutil,sys,struct,zlib
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE); OUT=os.path.join(ROOT,'site')
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
NAV=[('index.html','Home'),('counties/miami-dade/index.html','Miami-Dade'),('counties/broward/index.html','Broward'),('counties/palm-beach/index.html','Palm Beach'),('walk-in-vs-appointment/index.html','Walk-in vs appointment'),('fees-and-documents/index.html','Fees and documents'),('child-under-16/index.html','Child under 16'),('faq/index.html','FAQ')]
S=dict(pafl="https://passportfacilitylocator.travel.state.gov/",pafldata="https://passportfacilitylocator.travel.state.gov/data/Facilities.json",
 fees="https://travel.state.gov/content/travel/en/passports/how-apply/fees.html",times="https://travel.state.gov/content/travel/en/passports/how-apply/processing-times.html",
 adult="https://travel.state.gov/content/travel/en/passports/need-passport/apply-in-person.html",child="https://travel.state.gov/content/travel/en/passports/need-passport/under-16.html",
 under16="https://travel.state.gov/en/passports/apply/child/under-16.html",teen="https://travel.state.gov/en/passports/apply/child/16-17-year-old.html",
 forms="https://travel.state.gov/en/passports/apply/help/forms.html",citizenship="https://travel.state.gov/en/passports/apply/help/citizenship-evidence.html",
 photohelp="https://travel.state.gov/en/passports/apply/help/photos.html",
 renew="https://travel.state.gov/content/travel/en/passports/have-passport/renew.html",photos="https://travel.state.gov/content/travel/en/passports/how-apply/photos.html",
 miami="https://travel.state.gov/en/passports/apply/get-fast/make-appointment/miami.html",agency="https://travel.state.gov/en/passports/apply/get-fast/make-appointment.html",
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
CSS=open(os.path.join(HERE,'style.css')).read()
CHECKED={}
def ld(graph):
    raw=json.dumps({"@context":"https://schema.org","@graph":graph},ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    return f'<script type="application/ld+json">{raw}</script>'
def page(path,title,body,desc,checked=None,crumb=None,home=False,error=False,faq_items=None):
    when=checked or D
    if not error: CHECKED[path]=when
    warn_meta(path,title,desc)
    nav=''.join(f'<a href="{clean(p)}">{label}</a>' for p,label in NAV)
    url=None if error else BASE+clean(path)
    published=iso_date(when)
    graph=[]
    if home:
        graph.append({"@type":"WebSite","@id":BASE+"/#website","name":SITE_NAME,"url":BASE+"/","description":desc,"publisher":{"@id":BASE+"/#organization"}})
        graph.append({"@type":"Organization","@id":BASE+"/#organization","name":SITE_NAME,"url":BASE+"/","logo":{"@type":"ImageObject","url":BASE+"/apple-touch-icon.png"}})
    crumbs=[{"@type":"ListItem","position":1,"name":"Home","item":BASE+"/"}]
    if not home:
        item={"@type":"ListItem","position":2,"name":crumb or title}
        if url: item["item"]=url
        crumbs.append(item)
    graph.append({"@type":"BreadcrumbList","itemListElement":crumbs})
    if not error:
        graph.append({"@type":"Article","headline":title,"description":desc,"datePublished":published,"dateModified":published,"mainEntityOfPage":url,"image":BASE+"/og.png","author":{"@type":"Organization","name":SITE_NAME,"url":BASE+"/"},"publisher":{"@type":"Organization","name":SITE_NAME,"url":BASE+"/","logo":{"@type":"ImageObject","url":BASE+"/apple-touch-icon.png"}}})
    if faq_items:
        graph.append({"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":plain(a)}} for q,a in faq_items]})
    canon=f'<link rel="canonical" href="{url}">' if url else ''
    robots='<meta name="robots" content="noindex">' if error else ''
    verify=''
    if GOOGLE_SITE_VERIFICATION: verify+=f'<meta name="google-site-verification" content="{H.escape(GOOGLE_SITE_VERIFICATION)}" />'
    if MSVALIDATE_01: verify+=f'<meta name="msvalidate.01" content="{H.escape(MSVALIDATE_01)}">'
    og_url=f'<meta property="og:url" content="{url}">' if url else ''
    times='' if error else f'<meta property="article:published_time" content="{published}"><meta property="article:modified_time" content="{published}">'
    og_type='website' if home or error else 'article'
    img=BASE+'/og.png'
    head_extra=(f'{canon}{robots}{verify}<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{H.escape(SITE_NAME)}">'
        f'<meta property="og:title" content="{H.escape(title)}"><meta property="og:description" content="{H.escape(desc)}">{og_url}'
        f'<meta property="og:image" content="{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{H.escape(SITE_NAME)}"><meta property="og:locale" content="en_US">{times}'
        f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{H.escape(title)}"><meta name="twitter:description" content="{H.escape(desc)}"><meta name="twitter:image" content="{img}">'
        f'<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">{ld(graph)}')
    h=f'''<!doctype html><html lang="en-US"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{H.escape(title)}</title><meta name="description" content="{H.escape(desc)}">{head_extra}<style>{CSS}</style><script defer src="/_vercel/insights/script.js"></script></head><body>
<header><a href="/">{SITE_NAME}</a><nav>{nav}</nav></header><main><p class="disclaimer">{H.escape(SHORT_DISCLAIMER)} <a href="/disclaimer/">Full disclaimer</a>.</p><p class="checked">Last checked: {when}</p>{body}</main>
<footer><p>Independent, unofficial guide. Not affiliated with the U.S. Department of State, USPS, any clerk of court or library. We do not sell or promote expediting services. Facility data comes from the official Passport Acceptance Facility Locator{src('pafl')}; rules and fees from travel.state.gov. Always confirm hours with the facility before you go. Last checked: {when}.</p><p>{H.escape(DISCLAIMER)}</p><p><a href="/disclaimer/">Disclaimer</a></p><p class="related">Related guides: <a href="https://south-florida-dmv-walkin-guide.vercel.app/" rel="noopener">South Florida DMV walk-in guide</a> and <a href="https://south-florida-dog-beaches.vercel.app/" rel="noopener">South Florida dog beaches</a>.</p></footer></body></html>'''
    assert '\u2014' not in h and '\u2013' not in h, path
    p=os.path.join(OUT,path); d=os.path.dirname(p)
    if d: os.makedirs(d,exist_ok=True)
    open(p,'w').write(h)
def hrs_html(h):
    if not h: return 'Not stated by source'
    return '<br>'.join(f"{DAYS[d][:3]}: {v[0]} <span class='lv {'ok' if v[1]==0 else 'comm'}'>{'walk-in' if v[1]==0 else 'appointment'}</span>" for d,v in sorted(h.items()))
def table(rows,showcounty=False):
    t='<input id="q" placeholder="Filter by city, ZIP or name" oninput="var v=this.value.toLowerCase();document.querySelectorAll(\'table tr\').forEach(function(r){if(r.querySelector(\'td\'))r.style.display=r.textContent.toLowerCase().indexOf(v)>-1?\'\':\'none\'})"><div class="wrap"><table><tr><th>Facility</th><th>Address</th>'+('<th>County</th>' if showcounty else '')+'<th>Acceptance hours (locator)</th><th>Walk-in?</th><th>Phone / website</th><th>Notes and source</th></tr>'
    for r in sorted(rows,key=lambda x:(x['city'],x['name'])):
        wk='Yes, some hours' if r['walk'] else ('No, appointment flagged for all listed hours' if r['appt_only'] else 'Not stated by source')
        ft=', '.join(k for k,v in r['feat'].items() if v) or 'None flagged'
        o=''.join(f'<br><span class="src">{H.escape(e["fact"])} [<a href="{e["url"]}" rel="noopener">operator page</a>]</span>' for e in r.get('official',[]))
        cf=f'<br><span class="lv comm">Conflict</span> <span class="src">{H.escape(r["conflict"])}</span>' if r['conflict'] else ''
        web=f'<br><a href="{H.escape(r["web"])}" rel="noopener">website</a>' if r['web'] else ''
        t+=f'<tr><td><strong>{H.escape(r["name"])}</strong><br><span class="src">{r["kind"]}</span></td><td>{H.escape(r["street"])}<br>{H.escape(r["city"])}, FL {r["zip"]}</td>'+(f'<td>{r["county"]}</td>' if showcounty else '')+f'<td>{hrs_html(r["hours"])}</td><td>{wk}</td><td>{r["phone"]}{web}</td><td><span class="src">Locator comment: "{H.escape(r["comment"]) or "none"}". Features: {ft}.</span>{o}{cf} <span class="src">[<a href="{S["pafl"]}" rel="noopener">source</a>]</span></td></tr>'
    return t+'</table></div>'
MIAMI=f'''<div class="card"><strong>Miami Passport Agency (urgent travel only)</strong><p>Omni Center, 1501 Biscayne Blvd, Suite 400, Miami, FL 33132. Monday to Friday 7:00 a.m. to 2:00 p.m., closed weekends and federal holidays. By appointment only. Miami is in a State Department pilot with the Detroit and San Juan passport agencies: you can make an appointment for urgent international travel within 21 calendar days, or if you need a foreign visa within 28 calendar days. Appointments: 877-487-2778{src('miami')}. This is not an acceptance facility; routine applications go to the places listed on this site.</p></div>'''
CALL='<div class="card note"><strong>Call or check online before you go.</strong> The locator says to check with the facility whether you need an appointment{0}. USPS locations direct you to usps.com/scheduler{1}. Hours below are as published in the official locator data on the date shown.</div>'.format(src('adult'),src('usps'))
cc={k:[r for r in recs if r['county']==v] for k,v in COUNTIES.items()}
nwalk=sum(r['walk'] for r in recs); ncon=sum(1 for r in recs if r['conflict'])
if os.path.exists(OUT): shutil.rmtree(OUT)
body=f'''<h1>Where to apply for a U.S. passport in South Florida</h1><p>{len(recs)} passport acceptance facilities in Miami-Dade, Broward and Palm Beach counties, from the State Department's official locator data on {D}{src('pafl')}, with acceptance hours and whether those hours are walk-in or appointment.</p>{CALL}
<h2>By county</h2><ul class="grid">'''+''.join(f'<li><a href="/counties/{k}/">{v}</a> ({len(cc[k])} facilities, {sum(r["walk"] for r in cc[k])} with some walk-in hours)</li>' for k,v in COUNTIES.items())+f'''</ul>
<h2>Who needs to apply in person</h2><div class="card"><ul><li>First-time adult applicants, and adults whose passport was lost, stolen or damaged, issued over 15 years ago, or issued when they were under 16, must apply in person with Form DS-11{src('adult')}.</li>
<li>All children under 16 must apply in person, usually with both parents or guardians{src('child')}. <a href="/child-under-16/">What to bring for a child under 16</a>.</li><li>Eligible adults can renew by mail (DS-82) or online, and postal employees should not charge the $35 facility fee for a DS-82 renewal{src('renew')}.</li></ul></div>
<h2>Quick links</h2><ul><li><a href="/walk-in-vs-appointment/">Walk-in vs appointment: every facility with walk-in hours</a></li><li><a href="/fees-and-documents/">Fees, DS-11 vs DS-82, documents, photos, processing times</a></li><li><a href="/child-under-16/">Passport for a child under 16: consent, documents and fees</a></li><li><a href="/faq/">FAQ</a></li></ul>
{MIAMI}'''
page('index.html',"South Florida passport acceptance facilities, walk-in hours",body,"Passport acceptance facilities in Miami-Dade, Broward and Palm Beach with walk-in vs appointment hours, from official State Department locator data.",home=True)
for k,v in COUNTIES.items():
    note=''.join(f'<div class="card"><strong>{H.escape(e["title"])}</strong><p>{H.escape(e["fact"])} <span class="src">[<a href="{e["url"]}" rel="noopener">source</a>]</span></p></div>' for e in {x['title']:x for x in extra if x['county']==v}.values())
    b=f'<h1>Passport acceptance facilities in {v}</h1><p>{len(cc[k])} facilities in the official locator, {sum(r["walk"] for r in cc[k])} with at least some hours flagged walk-in. County is assigned from the facility ZIP code using the Census 2020 ZCTA to county file{src("census")}.</p>{CALL}{note}<p>Applying for a child under 16: <a href="/child-under-16/">both parents, the consent form, documents and fees</a>.</p>'+table(cc[k])+(MIAMI if k=='miami-dade' else '')
    page(f'counties/{k}/index.html',f"Passport acceptance facilities in {v}, FL",b,f"Passport acceptance facilities in {v} with hours, walk-in or appointment, from official State Department locator data.",crumb=v)
wr=[r for r in recs if r['walk']]
b=f'''<h1>Passport walk-in vs appointment in South Florida</h1>
<div class="card"><p>The official locator marks each block of acceptance hours. Its "Walk-in hours" filter counts only hours not flagged "By Appointment"{src('pafl')}. On {D}: <strong>{nwalk}</strong> of {len(recs)} South Florida facilities have at least some walk-in hours; the rest are appointment-flagged for all listed hours. Every USPS location in the data shows "To schedule a passport appointment or view additional passport acceptance times, please visit www.usps.com/scheduler."{src('usps')}</p>
<p>{ncon} facilities have a conflict between the locator's walk-in flag and the comment text or the operator's own page. They are marked Conflict below. Trust the operator and call.</p></div>
<h2>Facilities with some walk-in hours</h2>{table(wr,True)}
<h2>What operators say on their own pages</h2>'''+''.join(f'<div class="card"><strong>{H.escape(e["title"])}</strong><p>{H.escape(e["fact"])} <span class="src">[<a href="{e["url"]}" rel="noopener">source</a>]</span></p></div>' for e in {x['title']:x for x in extra}.values())+MIAMI
page('walk-in-vs-appointment/index.html',"Passport walk-in vs appointment hours in South Florida",b,"Which South Florida passport acceptance facilities accept walk-ins and which need appointments, with source conflicts flagged.",crumb="Walk-in vs appointment")
fb=f'''<h1>U.S. passport fees, forms and documents</h1><p>All amounts as stated by travel.state.gov on {D}.</p>
<h2>Which form</h2><div class="card"><ul><li><strong>DS-11 (in person)</strong>: first-time adults, children under 16, and adults whose passport was lost, stolen, damaged, issued over 15 years ago, or issued when under 16{src('adult','child')}.</li>
<li><strong>DS-82 (renew by mail)</strong>: you can submit your most recent passport, it was never reported lost or stolen, issued within the last 15 years, issued when you were 16 or older and valid for 10 years, in your current name (or you have a name change document), and not damaged beyond normal wear{src('renew')}.</li>
<li>Children's passports cannot be renewed; apply in person each time{src('child')}. <a href="/child-under-16/">Child under 16 in South Florida</a> covers consent, custody proof and minor fees.</li></ul></div>
<h2>Fees (DS-11, in person)</h2><div class="wrap"><table><tr><th>Document</th><th>Adult 16+ application fee</th><th>Child under 16 application fee</th><th>Facility acceptance fee</th></tr>
<tr><td>Passport book</td><td>$130</td><td>$100</td><td>$35</td></tr><tr><td>Passport card</td><td>$30</td><td>$15</td><td>$35</td></tr><tr><td>Book and card</td><td>$160</td><td>$115</td><td>$35</td></tr></table></div><p class="src">Source: {src('fees')}</p>
<h2>Fees (DS-82 renewal by mail or online)</h2><div class="wrap"><table><tr><th>Document</th><th>Application fee</th></tr><tr><td>Passport book</td><td>$130</td></tr><tr><td>Passport card</td><td>$30</td></tr><tr><td>Book and card</td><td>$160</td></tr></table></div><p>No facility acceptance fee{src('fees','renew')}.</p>
<h2>Optional fees</h2><div class="card"><ul><li>Expedited service: $60 per application{src('fees')}.</li><li>1 to 3 day return delivery: $26.87 (not offered for card-only applications){src('fees')}.</li><li>File search if you cannot get evidence of citizenship: $150 when the missing passport or Consular Report of Birth Abroad was issued before 1994. If that record was issued in 1994 or later, do not pay the $150 when you apply. The State Department may ask for the $150 later if an electronic search does not find the record{src('fees','citizenship')}.</li><li>Faster shipping of your application to the State Department: paid to the acceptance facility; cost varies by location{src('fees')}.</li></ul></div>
<h2>How to pay at an acceptance facility</h2><div class="card"><p>Application fee: check (personal, certified, cashier's, traveler's) or money order payable to "U.S. Department of State", with the applicant's name and date of birth in the memo{src('fees')}. The $35 acceptance fee is paid to the facility; ask the facility what it accepts{src('fees')}. Example: Palm Beach Clerk accepts cash, a personal check, a cashier's check, a money order, MasterCard, Visa, American Express, or Discover for its $35 execution fee, and only a personal check, a cashier's check, or a money order for the State Department fee{src('pbcfees')}. Passport photos there are $16 each, and free for veterans, active-duty service members, and reservists who show a military discharge form (DD-214), military identification, or a veteran designation on a driver's license{src('pbc')}.</p></div>
<h2>Documents to bring (DS-11)</h2><div class="card"><ul><li>The DS-11, printed single-sided. Do not sign until the acceptance agent asks{src('adult')}.</li><li>Physical evidence of U.S. citizenship (for example a U.S. birth certificate, a full-validity undamaged passport, a Consular Report of Birth Abroad, or a Certificate of Naturalization or Citizenship) plus a photocopy. Digital or mobile birth certificates are not accepted{src('adult')}.</li>
<li>A physical photo ID such as a valid driver's license, plus a photocopy of front and back on 8.5 x 11 inch single-sided paper. If your ID is from another state, bring a second photo ID{src('adult')}.</li><li>One passport photo{src('adult','photos')}.</li>
<li>Children: proof of relationship, both parents' IDs, and if a parent cannot attend, Form DS-3053 notarized within 90 days, or other documents listed by the State Department{src('child')}. Full checklist: <a href="/child-under-16/">child under 16</a>.</li></ul></div>
<h2>Photo rules (summary)</h2><div class="card"><ul><li>1 color photo taken in the last 6 months, 2 x 2 inches (51 x 51 mm), head 1 to 1 3/8 inches (25 to 35 mm) chin to top of head{src('photos')}.</li><li>Plain white or off-white background, no shadows, no filters or edits{src('photos')}.</li><li>No glasses. Hats or head coverings only for documented religious or medical reasons, with a signed statement{src('photos')}.</li><li>No uniforms, camouflage or headphones; you may smile with mouth closed{src('photos')}.</li></ul></div>
<h2>Processing times (as officially stated)</h2><div class="card"><ul><li>Routine: 4 to 6 weeks. Expedited: 2 to 3 weeks{src('times')}.</li><li>Mailing is not included: up to 2 weeks to reach the State Department and up to 2 weeks to receive the passport{src('times')}.</li><li>Urgent travel needs an appointment at a passport agency and proof of international travel within 14 calendar days{src('times')}. The Miami Passport Agency is in a pilot that allows an appointment within 21 calendar days of travel, or within 28 calendar days if you need a foreign visa{src('miami')}. Busiest season is late winter to summer; October to December is quieter{src('times')}.</li></ul></div>{MIAMI}'''
page('fees-and-documents/index.html',"Passport fees, DS-11 vs DS-82, documents and photo rules",fb,"Official U.S. passport fees, which form to use, documents, photo rules and processing times published on travel.state.gov.",crumb="Fees and documents")
faq=[("Can I walk in at a post office?",f"USPS listings in the locator point to usps.com/scheduler for appointments and additional times{src('usps','pafl')}. Some USPS hours in the data are flagged walk-in. See the <a href=\"/walk-in-vs-appointment/\">walk-in page</a>."),
("Which South Florida offices say they take walk-ins?",f"Broward Clerk of Courts lists passport hours at its Central, North, South and West courthouses{src('broward')}, and the locator comments for its regional courthouses say appointments are not required{src('pafl')}. Palm Beach Clerk says walk-in customers are not accepted{src('pbc')}. Miami-Dade Public Library says its passport service is by appointment only{src('mdpls')}."),
("How much does a first adult passport book cost?",f"$130 to the U.S. Department of State plus $35 to the acceptance facility{src('fees')}."),
("Can I renew at an acceptance facility?",f"If you are eligible for DS-82, you renew by mail or online. Postal employees should not charge the $35 fee or review a DS-82{src('renew')}."),
("I travel in less than two weeks. Where do I go?",f"Most passport agencies take an appointment once you are within 14 calendar days of international travel, or within 28 calendar days if you need a foreign visa. The Miami Passport Agency is in a pilot that allows an appointment within 21 calendar days of urgent travel, or within 28 calendar days if you need a foreign visa. Call 877-487-2778{src('miami','times')}."),
("Do I need both parents for a child's passport?",f"For a child under 16, both parents or guardians must be present or give approval, for example with a notarized DS-3053. Sole custody uses different documents, and ages 16 and 17 follow another rule. <a href=\"/child-under-16/\">Child under 16</a>.{src('under16','teen')}"),
("Can I bring a digital birth certificate?",f"No. Physical evidence of citizenship only{src('adult')}."),
("Do facilities take photos?",f"Some do; the locator flags 'photos on site'{src('pafl')}. Palm Beach Clerk sells photos for $16 each, and that photo is free for veterans, active-duty service members, and reservists who show military identification or a discharge form{src('pbc')}. Miami-Dade libraries say photo service is not currently available{src('mdpls')}.")]
page('faq/index.html',"South Florida passport FAQ: walk-ins, fees, documents",'<h1>Passport FAQ for South Florida</h1>'+''.join(f'<div class="card"><strong>{q}</strong><p>{a}</p></div>' for q,a in faq),"Short sourced answers on walk-in hours, fees, documents and applying for a U.S. passport in Miami-Dade, Broward and Palm Beach.",crumb="FAQ",faq_items=faq)
CHILD=f'''<h1>Passport for a child under 16 in South Florida</h1>
<p>A child under 16 applies in person with Form DS-11 at a passport acceptance facility. Bring the child. You cannot renew a child's passport, and the passport is valid for 5 years. Both parents or guardians go with the child, or you bring the consent or custody documents below.{src('under16')}</p>
<div class="card note"><strong>Ages 16 and 17 use different rules.</strong> They still apply in person on DS-11, but only one parent or guardian has to show they know about the application, the passport is valid for 10 years, and the fees are the adult fees. Those rules are at the end of this page.{src('teen')}</div>
<h2>Where to apply in Miami-Dade, Broward and Palm Beach</h2>
<p>Use an acceptance facility (post office, clerk of court, or library) if international travel is more than 3 weeks away, and ask whether that office needs an appointment. If the child is traveling internationally in less than 3 weeks, make an appointment at a passport agency once you are within 14 calendar days of travel.{src('under16')} The Miami Passport Agency is in a pilot that allows an appointment within 21 calendar days of urgent travel, or within 28 calendar days if you need a foreign visa.{src('miami')} Facilities: <a href="/counties/miami-dade/">Miami-Dade</a>, <a href="/counties/broward/">Broward</a>, <a href="/counties/palm-beach/">Palm Beach</a>.</p>
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
<div class="wrap"><table><tr><th>Document</th><th>Form</th><th>Application fee</th><th>Facility acceptance fee</th></tr>
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
page('child-under-16/index.html',"U.S. passport for a child under 16 in South Florida",CHILD,"How to apply for a U.S. passport for a child under 16 in Miami-Dade, Broward and Palm Beach: DS-11, both parents, DS-3053, custody proof, documents and fees.",checked="26 October 2026",crumb="Child under 16")
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
page('disclaimer/index.html',"Disclaimer for this South Florida passport acceptance guide",DISC,"Accuracy, no warranty, limitation of liability, external links, affiliation, official sources and corrections for this passport guide.",checked="26 October 2026",crumb="Disclaimer")
HUBS=[('/','Home'),('/counties/miami-dade/','Miami-Dade County'),('/counties/broward/','Broward County'),('/counties/palm-beach/','Palm Beach County'),('/walk-in-vs-appointment/','Walk-in vs appointment'),('/fees-and-documents/','Fees and documents'),('/child-under-16/','Child under 16'),('/faq/','FAQ')]
page('404.html',"Page not found: South Florida passport acceptance guide",'<h1>Page not found</h1><p>That address is not on this site. Use the navigation above or one of these guides:</p><ul>'+''.join(f'<li><a href="{h}">{n}</a></li>' for h,n in HUBS)+'</ul>',"That address is not on this site. Browse passport acceptance facilities in Miami-Dade, Broward and Palm Beach, plus fees, documents and walk-in hours.",crumb="Page not found",error=True)
write_assets()
pages=[os.path.relpath(os.path.join(dp,f),OUT) for dp,_,fs in os.walk(OUT) for f in fs if f.endswith('.html') and f!='404.html']
open(os.path.join(OUT,'robots.txt'),'w').write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
open(os.path.join(OUT,'sitemap.xml'),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE+clean(p)}</loc><lastmod>{iso_date(CHECKED.get(p,D))}</lastmod></url>\n' for p in sorted(pages))+'</urlset>\n')
print(len(recs),'facilities',{k:len(v) for k,v in cc.items()},'walk',nwalk,'conflicts',ncon)
for r in recs:
    if r['conflict']: print(' C:',r['name'],'|',r['conflict'])
