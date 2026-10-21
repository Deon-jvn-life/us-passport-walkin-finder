#!/usr/bin/env python3
"""Build the South Florida passport acceptance facility site from JSON in tools/ into site/."""
import json,os,re,html as H,shutil
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE); OUT=os.path.join(ROOT,'site')
D="21 October 2026"; BASE="https://us-passport-walkin-finder.vercel.app"  # replace with real domain before deploy
S=dict(pafl="https://passportfacilitylocator.travel.state.gov/",pafldata="https://passportfacilitylocator.travel.state.gov/data/Facilities.json",
 fees="https://travel.state.gov/content/travel/en/passports/how-apply/fees.html",times="https://travel.state.gov/content/travel/en/passports/how-apply/processing-times.html",
 adult="https://travel.state.gov/content/travel/en/passports/need-passport/apply-in-person.html",child="https://travel.state.gov/content/travel/en/passports/need-passport/under-16.html",
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
    w=(web or '').strip()
    if w and not re.match(r'^https?://[A-Za-z0-9.-]+\.[a-z]{2,}',w,re.I) or '@' in w: w=''
    recs.append(dict(id=f['id'],name=n.title().replace('Usps','USPS').replace('Po ','PO ').replace("'S","'s"),street=street.title(),city=city.title(),zip=z,county=f['county'],
      phone=re.sub(r'(\d{3})(\d{3})(\d{4})',r'(\1) \2-\3',ph or '') or 'Not stated by source',web=w.lower() if w else '',feat=FEAT(int(feat or 0)),hours=h,walk=walk,appt_only=appt_only,
      comment=com,conflict=conflict,kind=kind,raw_hours=hrs))
for r in recs:
    for e in extra:
        if e['match'] in r['name'].upper() and e['county']==r['county'] and e['url'] not in [x['url'] for x in r.get('official',[])]: r.setdefault('official',[]).append(e)
for r in recs:
    for e in r.get('official',[]):
        if e.get('walkin') is False and r['walk']: r['conflict']=(r['conflict']+' ' if r['conflict'] else '')+f"The operator page says walk-ins are not accepted, but locator hours for this office are flagged walk-in."
json.dump(recs,open(os.path.join(HERE,'facilities_parsed.json'),'w'),indent=1)
CSS=open(os.path.join(HERE,'style.css')).read()
def page(path,title,body,desc):
    r='../'*path.count('/')
    nav=f'<a href="{r}index.html">Home</a>'+''.join(f'<a href="{r}counties/{k}/index.html">{v.replace(" County","")}</a>' for k,v in COUNTIES.items())+f'<a href="{r}walk-in-vs-appointment/index.html">Walk-in vs appointment</a><a href="{r}fees-and-documents/index.html">Fees and documents</a><a href="{r}faq/index.html">FAQ</a>'
    h=f'''<!doctype html><html lang="en-US"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{H.escape(title)}</title><meta name="description" content="{H.escape(desc)}"><link rel="canonical" href="{BASE}/{path.replace('index.html','')}"><style>{CSS}</style><script defer src="/_vercel/insights/script.js"></script></head><body>
<header><a href="{r}index.html">South Florida Passport Places</a><nav>{nav}</nav></header><main><p class="checked">Last checked: {D}</p>{body}</main>
<footer>Independent, unofficial guide. Not affiliated with the U.S. Department of State, USPS, any clerk of court or library. We do not sell or promote expediting services. Facility data comes from the official Passport Acceptance Facility Locator{src('pafl')}; rules and fees from travel.state.gov. Always confirm hours with the facility before you go. Last checked: {D}.</footer></body></html>'''
    assert '\u2014' not in h and '\u2013' not in h, path
    p=os.path.join(OUT,path); os.makedirs(os.path.dirname(p),exist_ok=True); open(p,'w').write(h)
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
MIAMI=f'''<div class="card"><strong>Miami Passport Agency (urgent travel only)</strong><p>Omni Center, 1501 Biscayne Blvd, Suite 400, Miami, FL 33132. Monday to Friday 7:00 a.m. to 2:00 p.m., closed weekends and federal holidays. By appointment only, for international travel within 14 calendar days or a foreign visa needed within 28 calendar days. Appointments: 877-487-2778{src('miami')}. This is not an acceptance facility; routine applications go to the places listed on this site.</p></div>'''
CALL='<div class="card note"><strong>Call or check online before you go.</strong> The locator says to check with the facility whether you need an appointment{0}. USPS locations direct you to usps.com/scheduler{1}. Hours below are as published in the official locator data on the date shown.</div>'.format(src('adult'),src('usps'))
cc={k:[r for r in recs if r['county']==v] for k,v in COUNTIES.items()}
nwalk=sum(r['walk'] for r in recs); ncon=sum(1 for r in recs if r['conflict'])
if os.path.exists(OUT): shutil.rmtree(OUT)
body=f'''<h1>Where to apply for a U.S. passport in South Florida</h1><p>{len(recs)} passport acceptance facilities in Miami-Dade, Broward and Palm Beach counties, from the State Department's official locator data on {D}{src('pafl')}, with acceptance hours and whether those hours are walk-in or appointment.</p>{CALL}
<h2>By county</h2><ul class="grid">'''+''.join(f'<li><a href="counties/{k}/index.html">{v}</a> ({len(cc[k])} facilities, {sum(r["walk"] for r in cc[k])} with some walk-in hours)</li>' for k,v in COUNTIES.items())+f'''</ul>
<h2>Who needs to apply in person</h2><div class="card"><ul><li>First-time adult applicants, and adults whose passport was lost, stolen or damaged, issued over 15 years ago, or issued when they were under 16, must apply in person with Form DS-11{src('adult')}.</li>
<li>All children under 16 must apply in person, usually with both parents or guardians{src('child')}.</li><li>Eligible adults can renew by mail (DS-82) or online, and postal employees should not charge the $35 facility fee for a DS-82 renewal{src('renew')}.</li></ul></div>
<h2>Quick links</h2><ul><li><a href="walk-in-vs-appointment/index.html">Walk-in vs appointment: every facility with walk-in hours</a></li><li><a href="fees-and-documents/index.html">Fees, DS-11 vs DS-82, documents, photos, processing times</a></li><li><a href="faq/index.html">FAQ</a></li></ul>
{MIAMI}'''
page('index.html',"South Florida passport acceptance facilities and walk-in hours",body,"Passport acceptance facilities in Miami-Dade, Broward and Palm Beach with walk-in vs appointment hours, from official State Department locator data.")
for k,v in COUNTIES.items():
    note=''.join(f'<div class="card"><strong>{H.escape(e["title"])}</strong><p>{H.escape(e["fact"])} <span class="src">[<a href="{e["url"]}" rel="noopener">source</a>]</span></p></div>' for e in {x['title']:x for x in extra if x['county']==v}.values())
    b=f'<h1>Passport acceptance facilities in {v}</h1><p>{len(cc[k])} facilities in the official locator, {sum(r["walk"] for r in cc[k])} with at least some hours flagged walk-in. County is assigned from the facility ZIP code using the Census 2020 ZCTA to county file{src("census")}.</p>{CALL}{note}'+table(cc[k])+(MIAMI if k=='miami-dade' else '')
    page(f'counties/{k}/index.html',f"Passport acceptance facilities in {v}, FL",b,f"Passport acceptance facilities in {v} with hours, walk-in or appointment, from official locator data.")
wr=[r for r in recs if r['walk']]
b=f'''<h1>Passport walk-in vs appointment in South Florida</h1>
<div class="card"><p>The official locator marks each block of acceptance hours. Its "Walk-in hours" filter counts only hours not flagged "By Appointment"{src('pafl')}. On {D}: <strong>{nwalk}</strong> of {len(recs)} South Florida facilities have at least some walk-in hours; the rest are appointment-flagged for all listed hours. Every USPS location in the data shows "To schedule a passport appointment or view additional passport acceptance times, please visit www.usps.com/scheduler."{src('usps')}</p>
<p>{ncon} facilities have a conflict between the locator's walk-in flag and the comment text or the operator's own page. They are marked Conflict below. Trust the operator and call.</p></div>
<h2>Facilities with some walk-in hours</h2>{table(wr,True)}
<h2>What operators say on their own pages</h2>'''+''.join(f'<div class="card"><strong>{H.escape(e["title"])}</strong><p>{H.escape(e["fact"])} <span class="src">[<a href="{e["url"]}" rel="noopener">source</a>]</span></p></div>' for e in {x['title']:x for x in extra}.values())+MIAMI
page('walk-in-vs-appointment/index.html',"Passport walk-in vs appointment: South Florida",b,"Which South Florida passport acceptance facilities accept walk-ins and which need appointments, with conflicts flagged.")
fb=f'''<h1>U.S. passport fees, forms and documents</h1><p>All amounts as stated by travel.state.gov on {D}.</p>
<h2>Which form</h2><div class="card"><ul><li><strong>DS-11 (in person)</strong>: first-time adults, children under 16, and adults whose passport was lost, stolen, damaged, issued over 15 years ago, or issued when under 16{src('adult','child')}.</li>
<li><strong>DS-82 (renew by mail)</strong>: you can submit your most recent passport, it was never reported lost or stolen, issued within the last 15 years, issued when you were 16 or older and valid for 10 years, in your current name (or you have a name change document), and not damaged beyond normal wear{src('renew')}.</li>
<li>Children's passports cannot be renewed; apply in person each time{src('child')}.</li></ul></div>
<h2>Fees (DS-11, in person)</h2><div class="wrap"><table><tr><th>Document</th><th>Adult 16+ application fee</th><th>Child under 16 application fee</th><th>Facility acceptance fee</th></tr>
<tr><td>Passport book</td><td>$130</td><td>$100</td><td>$35</td></tr><tr><td>Passport card</td><td>$30</td><td>$15</td><td>$35</td></tr><tr><td>Book and card</td><td>$160</td><td>$115</td><td>$35</td></tr></table></div><p class="src">Source: {src('fees')}</p>
<h2>Fees (DS-82 renewal by mail or online)</h2><div class="wrap"><table><tr><th>Document</th><th>Application fee</th></tr><tr><td>Passport book</td><td>$130</td></tr><tr><td>Passport card</td><td>$30</td></tr><tr><td>Book and card</td><td>$160</td></tr></table></div><p>No facility acceptance fee{src('fees','renew')}.</p>
<h2>Optional fees</h2><div class="card"><ul><li>Expedited service: $60 per application{src('fees')}.</li><li>1 to 3 day return delivery: $26.87 (not offered for card-only applications){src('fees')}.</li><li>File search if you cannot get evidence of citizenship: $150{src('fees')}.</li><li>Faster shipping of your application to the State Department: paid to the acceptance facility; cost varies by location{src('fees')}.</li></ul></div>
<h2>How to pay at an acceptance facility</h2><div class="card"><p>Application fee: check (personal, certified, cashier's, traveler's) or money order payable to "U.S. Department of State", with the applicant's name and date of birth in the memo{src('fees')}. The $35 acceptance fee is paid to the facility; ask the facility what it accepts{src('fees')}. Example: Palm Beach Clerk accepts cash, check, money order and major cards for its $35 execution fee, and only check or money order for the State Department fee{src('pbcfees')}.</p></div>
<h2>Documents to bring (DS-11)</h2><div class="card"><ul><li>The DS-11, printed single-sided. Do not sign until the acceptance agent asks{src('adult')}.</li><li>Physical evidence of U.S. citizenship (for example a U.S. birth certificate, a full-validity undamaged passport, a Consular Report of Birth Abroad, or a Certificate of Naturalization or Citizenship) plus a photocopy. Digital or mobile birth certificates are not accepted{src('adult')}.</li>
<li>A physical photo ID such as a valid driver's license, plus a photocopy of front and back on 8.5 x 11 inch single-sided paper. If your ID is from another state, bring a second photo ID{src('adult')}.</li><li>One passport photo{src('adult','photos')}.</li>
<li>Children: proof of relationship, both parents' IDs, and if a parent cannot attend, Form DS-3053 notarized within 90 days, or other documents listed by the State Department{src('child')}.</li></ul></div>
<h2>Photo rules (summary)</h2><div class="card"><ul><li>1 color photo taken in the last 6 months, 2 x 2 inches (51 x 51 mm), head 1 to 1 3/8 inches (25 to 35 mm) chin to top of head{src('photos')}.</li><li>Plain white or off-white background, no shadows, no filters or edits{src('photos')}.</li><li>No glasses. Hats or head coverings only for documented religious or medical reasons, with a signed statement{src('photos')}.</li><li>No uniforms, camouflage or headphones; you may smile with mouth closed{src('photos')}.</li></ul></div>
<h2>Processing times (as officially stated)</h2><div class="card"><ul><li>Routine: 4 to 6 weeks. Expedited: 2 to 3 weeks{src('times')}.</li><li>Mailing is not included: up to 2 weeks to reach the State Department and up to 2 weeks to receive the passport{src('times')}.</li><li>Urgent travel needs an appointment at a passport agency and proof of international travel within 14 calendar days{src('times')}. Busiest season is late winter to summer; October to December is quieter{src('times')}.</li></ul></div>{MIAMI}'''
page('fees-and-documents/index.html',"U.S. passport fees, DS-11 vs DS-82, documents and photo rules",fb,"Official U.S. passport fees, which form to use, documents, photo rules and processing times from travel.state.gov.")
faq=[("Can I walk in at a post office?",f"USPS listings in the locator point to usps.com/scheduler for appointments and additional times{src('usps','pafl')}. Some USPS hours in the data are flagged walk-in. See the <a href=\"../walk-in-vs-appointment/index.html\">walk-in page</a>."),
("Which South Florida offices say they take walk-ins?",f"Broward Clerk of Courts lists passport hours at its Central, North, South and West courthouses{src('broward')}, and the locator comments for its regional courthouses say appointments are not required{src('pafl')}. Palm Beach Clerk says walk-in customers are not accepted{src('pbc')}. Miami-Dade Public Library says its passport service is by appointment only{src('mdpls')}."),
("How much does a first adult passport book cost?",f"$130 to the U.S. Department of State plus $35 to the acceptance facility{src('fees')}."),
("Can I renew at an acceptance facility?",f"If you are eligible for DS-82, you renew by mail or online. Postal employees should not charge the $35 fee or review a DS-82{src('renew')}."),
("I travel in less than two weeks. Where do I go?",f"Make an appointment at a passport agency within 14 days of travel. The nearest is the Miami Passport Agency; call 877-487-2778{src('miami','times')}."),
("Do I need both parents for a child's passport?",f"Both parents or guardians must be present or give approval, for example with a notarized DS-3053{src('child')}."),
("Can I bring a digital birth certificate?",f"No. Physical evidence of citizenship only{src('adult')}."),
("Do facilities take photos?",f"Some do; the locator flags 'photos on site'{src('pafl')}. Palm Beach Clerk sells photos for $16 each{src('pbc')}. Miami-Dade libraries say photo service is not currently available{src('mdpls')}.")]
page('faq/index.html',"South Florida passport FAQ",'<h1>Passport FAQ for South Florida</h1>'+''.join(f'<div class="card"><strong>{q}</strong><p>{a}</p></div>' for q,a in faq),"Short sourced answers about applying for a U.S. passport in Miami-Dade, Broward and Palm Beach.")
pages=[os.path.relpath(os.path.join(dp,f),OUT) for dp,_,fs in os.walk(OUT) for f in fs if f.endswith('.html')]
open(os.path.join(OUT,'robots.txt'),'w').write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
open(os.path.join(OUT,'sitemap.xml'),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE}/{p.replace("index.html","")}</loc><lastmod>2026-10-21</lastmod></url>\n' for p in sorted(pages))+'</urlset>\n')
print(len(recs),'facilities',{k:len(v) for k,v in cc.items()},'walk',nwalk,'conflicts',ncon)
for r in recs:
    if r['conflict']: print(' C:',r['name'],'|',r['conflict'])
