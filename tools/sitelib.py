"""Page shell: topic menu, sticky header, search, breadcrumbs, on-this-page, read next."""
import os, html as H, shutil, re, json

D = "26 October 2026"
ISO = "2026-10-26"
BASE_DEFAULT = "https://us-passport-walkin-finder.vercel.app"

def esc(s):
    return H.escape(s, quote=True)

def slug(t):
    t = H.unescape(re.sub(r'<[^>]+>', '', t))
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')

def href(path):
    if path in ('index.html', '/'):
        return '/'
    if path.endswith('/index.html'):
        return '/' + path[:-len('index.html')]
    return '/' + path

def canon_url(base, path):
    return base.rstrip('/') + href(path)

SEARCH_JS = r'''(function(){
  var el=document.getElementById("search-data");
  var input=document.getElementById("q");
  var box=document.getElementById("search-results");
  if(!el||!input||!box) return;
  var pages=[];
  try { pages=JSON.parse(el.textContent); } catch(e){ return; }
  function escHtml(s){
    return String(s).replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];
    });
  }
  function activeWords(q){
    var t=String(q||"").trim().toLowerCase();
    if(t.length<2) return [];
    return t.split(/\s+/).filter(function(w){ return w; });
  }
  function match(blob, ws){
    if(!ws.length) return true;
    blob=String(blob).toLowerCase();
    for(var i=0;i<ws.length;i++) if(blob.indexOf(ws[i])<0) return false;
    return true;
  }
  function filterIndex(q){
    var root=document.getElementById("page-index");
    if(!root) return;
    var ws=activeWords(q);
    var items=root.querySelectorAll("li");
    var shown=0;
    for(var i=0;i<items.length;i++){
      var li=items[i];
      var blob=li.textContent+" "+(li.getAttribute("data-keywords")||"");
      var ok=match(blob, ws);
      li.hidden=!ok;
      if(ok) shown++;
    }
    var sections=root.querySelectorAll("section");
    for(var s=0;s<sections.length;s++){
      var sec=sections[s];
      var lis=sec.querySelectorAll("li");
      var any=false;
      for(var k=0;k<lis.length;k++) if(!lis[k].hidden) any=true;
      sec.hidden=!any;
    }
    var status=document.getElementById("index-status");
    if(status){
      if(!ws.length) status.textContent="Showing every page.";
      else if(!shown) status.textContent="No page matches. Try a different word, or clear the search.";
      else status.textContent="Showing "+shown+" of "+items.length+" pages.";
    }
  }
  function show(q){
    var ws=activeWords(q);
    if(!ws.length){
      box.hidden=true;
      box.innerHTML="";
    } else {
      var hits=[];
      for(var i=0;i<pages.length;i++){
        var p=pages[i];
        var blob=p.t+" "+p.s+" "+p.g+" "+(p.k||"");
        if(match(blob, ws)) hits.push(p);
        if(hits.length===8) break;
      }
      if(!hits.length){
        box.innerHTML="<p class=\"search-empty\">No matching page. Open the <a href=\"/find/\">full page list</a>.</p>";
      } else {
        var html="<ul>";
        for(var j=0;j<hits.length;j++){
          var hit=hits[j];
          html+="<li><a href=\""+escHtml(hit.u)+"\"><strong>"+escHtml(hit.t)+"</strong><span>"+escHtml(hit.s)+"</span></a></li>";
        }
        html+="</ul>";
        box.innerHTML=html;
      }
      box.hidden=false;
    }
    filterIndex(q);
  }
  input.addEventListener("input", function(){ show(input.value); });
  input.addEventListener("keydown", function(e){
    if(e.key==="Escape"){ box.hidden=true; box.innerHTML=""; }
  });
  document.addEventListener("click", function(e){
    if(!box.contains(e.target) && e.target!==input){ box.hidden=true; }
  });
  var initial="";
  try { initial=new URLSearchParams(window.location.search).get("q")||""; } catch(err){ initial=""; }
  if(initial){ input.value=initial; show(initial); }
  else filterIndex("");
  var sums=document.querySelectorAll(".grp > summary");
  for(var n=0;n<sums.length;n++){
    sums[n].addEventListener("click", function(){
      var parent=this.parentNode;
      var open=document.querySelectorAll(".grp[open]");
      for(var i=0;i<open.length;i++) if(open[i]!==parent) open[i].removeAttribute("open");
    });
  }
})();'''

DOCK_JS = r'''(function(){
  var header=document.getElementById("site-header");
  var slot=document.getElementById("head-slot");
  var toggle=document.querySelector(".search-toggle");
  var search=document.getElementById("site-search");
  var menu=document.querySelector("details.menu");
  if(!header||!slot) return;
  var docked=false;
  var fullH=0;
  function compactPx(){
    var raw=getComputedStyle(document.documentElement).getPropertyValue("--header-compact")||"72px";
    var n=parseFloat(raw);
    if(String(raw).indexOf("rem")>=0){
      n=n*parseFloat(getComputedStyle(document.documentElement).fontSize||"16");
    }
    return n||72;
  }
  function setSearchOpen(open){
    if(!search||!toggle) return;
    if(open && !document.body.classList.contains("is-docked")) open=false;
    search.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open?"true":"false");
    if(open){ if(menu) menu.removeAttribute("open"); closeGroups(); }
    if(open){
      var input=document.getElementById("q");
      if(input) input.focus();
    }
  }
  function measure(){
    if(docked) return;
    if(menu && menu.hasAttribute("open")) return;
    fullH=header.offsetHeight;
  }
  var nav=document.getElementById("site-nav");
  function closeGroups(){
    var open=document.querySelectorAll(".grp[open]");
    for(var i=0;i<open.length;i++) open[i].removeAttribute("open");
  }
  function updateHint(){
    if(!nav) return;
    var more=docked && nav.scrollWidth>nav.clientWidth+8;
    var atEnd=nav.scrollLeft+nav.clientWidth>=nav.scrollWidth-8;
    var atStart=nav.scrollLeft<=8;
    document.body.classList.toggle("nav-more-right", !!(more && !atEnd));
    document.body.classList.toggle("nav-more-left", !!(more && !atStart));
  }
  function revealCurrent(){
    if(!nav) return;
    var cur=nav.querySelector(".grp.has-current");
    if(!cur || nav.scrollWidth<=nav.clientWidth+8){ updateHint(); return; }
    var left=cur.offsetLeft-(nav.clientWidth-cur.offsetWidth)/2;
    nav.scrollLeft=left<0?0:left;
    updateHint();
  }
  function dock(){
    if(docked) return;
    if(menu) menu.removeAttribute("open");
    closeGroups();
    setSearchOpen(false);
    measure();
    if(!fullH) fullH=header.offsetHeight;
    slot.style.height=fullH+"px";
    document.body.classList.add("is-docked");
    docked=true;
    revealCurrent();
  }
  function undock(){
    if(!docked) return;
    setSearchOpen(false);
    closeGroups();
    if(menu) menu.removeAttribute("open");
    document.body.classList.remove("is-docked");
    document.body.classList.remove("nav-more-right");
    document.body.classList.remove("nav-more-left");
    slot.style.height="";
    docked=false;
    measure();
  }
  function onScroll(){
    var y=window.scrollY||document.documentElement.scrollTop||0;
    var line=fullH-compactPx();
    if(!fullH) measure();
    if(!docked){
      measure();
      if(fullH>compactPx() && y>fullH-compactPx()) dock();
    } else if(y<line-24){
      undock();
    }
  }
  if(toggle){
    toggle.addEventListener("click", function(){
      var open=toggle.getAttribute("aria-expanded")==="true";
      setSearchOpen(!open);
    });
  }
  if(menu){
    var sum=menu.querySelector("summary");
    if(sum) sum.addEventListener("click", function(){ setSearchOpen(false); });
  }
  document.addEventListener("keydown", function(e){
    if(e.key!=="Escape") return;
    setSearchOpen(false);
    closeGroups();
    if(menu && menu.hasAttribute("open")) menu.removeAttribute("open");
    var box=document.getElementById("search-results");
    if(box){ box.hidden=true; box.innerHTML=""; }
  });
  document.addEventListener("click", function(e){
    if(!docked||header.contains(e.target)) return;
    setSearchOpen(false);
    closeGroups();
    if(menu) menu.removeAttribute("open");
  });
  if(nav){
    nav.addEventListener("scroll", updateHint, {passive:true});
    var topicSums=nav.querySelectorAll(".grp>summary");
    for(var s=0;s<topicSums.length;s++){
      topicSums[s].addEventListener("click", function(){ setSearchOpen(false); });
    }
  }
  document.addEventListener("focusin", function(e){
    var t=e.target;
    if(!t||!docked) return;
    if(nav && nav.contains(t) && nav.scrollWidth>nav.clientWidth+8 && t.closest){
      var grp=t.closest(".grp");
      if(grp){
        var pad=16;
        var left=grp.offsetLeft-pad;
        var right=grp.offsetLeft+grp.offsetWidth+pad;
        if(left<nav.scrollLeft) nav.scrollLeft=Math.max(0,left);
        else if(right>nav.scrollLeft+nav.clientWidth) nav.scrollLeft=right-nav.clientWidth;
        updateHint();
      }
    }
    if(header.contains(t)||(t.classList&&t.classList.contains("skip"))) return;
    var edge=compactPx()+12;
    var r=t.getBoundingClientRect();
    if(r.bottom>edge && r.top>=edge) return;
    var y=(window.scrollY||0)+r.top-edge;
    window.scrollTo(0, y<0?0:y);
  });
  window.addEventListener("scroll", onScroll, {passive:true});
  window.addEventListener("resize", function(){
    if(docked) undock();
    measure();
    onScroll();
  });
  measure();
  onScroll();
})();'''

TOC_BOOT = '<script>if(window.matchMedia("(min-width:960px)").matches){var d=document.currentScript.previousElementSibling;if(d&&d.tagName==="DETAILS")d.open=true;}</script>'

MARK = ('<svg class="mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
        '<rect width="32" height="32" rx="6" fill="#F4F7FB"/>'
        '<rect x="8" y="5" width="16" height="22" rx="1.5" fill="#F4F7FB" stroke="#0C1B33" stroke-width="1.5"/>'
        '<circle cx="16" cy="13" r="3.1" fill="none" stroke="#0C1B33" stroke-width="1.5"/>'
        '<rect x="11" y="19.5" width="10" height="1.5" rx="0.75" fill="#0C1B33"/>'
        '<rect x="12.2" y="22.5" width="7.6" height="1.5" rx="0.75" fill="#0C1B33"/></svg>')

def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _lum(hex_color):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

def _contrast(a, b):
    L1, L2 = _lum(a), _lum(b)
    lighter, darker = max(L1, L2), min(L1, L2)
    return (lighter + 0.05) / (darker + 0.05)

def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _mix(a, b, t):
    A, B = _hex_to_rgb(a), _hex_to_rgb(b)
    rgb = tuple(round(A[i] + (B[i] - A[i]) * t) for i in range(3))
    return '#{:02X}{:02X}{:02X}'.format(*rgb)

def check_header_contrast(css):
    """Fail the build if white text or the gold focus ring misses WCAG AA on any gradient stop."""
    m = re.search(r'--head-bg:\s*linear-gradient\(\s*[\d.]+deg\s*,([^)]+)\)', css)
    if not m:
        raise SystemExit('Header gradient missing from CSS')
    parts = [p.strip() for p in m.group(1).split(',')]
    stops = []
    for p in parts:
        cm = re.search(r'(#[0-9A-Fa-f]{6})\s+([\d.]+)%', p)
        if not cm:
            raise SystemExit('Unparsed gradient stop: ' + p)
        stops.append((cm.group(1).upper(), float(cm.group(2)) / 100))
    if len(stops) < 2:
        raise SystemExit('Need at least two gradient stops')
    worst_text, worst_gold = 99, 99
    worst_text_at = worst_gold_at = ''
    steps = 201
    for i in range(steps):
        t = i / (steps - 1)
        for (c0, t0), (c1, t1) in zip(stops, stops[1:]):
            if t0 <= t <= t1 and t1 > t0:
                col = _mix(c0, c1, (t - t0) / (t1 - t0))
                tw, gw = _contrast('#FFFFFF', col), _contrast('#FFE08A', col)
                if tw < worst_text:
                    worst_text, worst_text_at = tw, col
                if gw < worst_gold:
                    worst_gold, worst_gold_at = gw, col
                break
    if worst_text < 4.5:
        raise SystemExit(f'Header text contrast {worst_text:.2f} at {worst_text_at} is under 4.5:1')
    if worst_gold < 3:
        raise SystemExit(f'Header focus gold contrast {worst_gold:.2f} at {worst_gold_at} is under 3:1')
    pairs = [
        ('#1A1814', '#FFE08A', 4.5),
        ('#1A1814', '#F4F1EA', 4.5),
        ('#1A1814', '#FFFFFF', 4.5),
        ('#0A3D66', '#F4F1EA', 4.5),
        ('#0A3D66', '#FFFFFF', 4.5),
        ('#0A3D66', '#FFF6DB', 4.5),
        ('#0A3D66', '#FFF8EC', 4.5),
        ('#0A3D66', '#EEF4F1', 4.5),
        ('#3D2A6B', '#F4F1EA', 4.5),
        ('#3D2A6B', '#FFFFFF', 4.5),
        ('#3E3A34', '#FFFFFF', 4.5),
        ('#3E3A34', '#F4F1EA', 4.5),
        ('#3E3A34', '#FFF8EC', 4.5),
        ('#1A1814', '#DFF3E4', 4.5),
        ('#1A1814', '#FDEBD3', 4.5),
        ('#1A1814', '#E7EFE9', 4.5),
        ('#143024', '#E5F2EA', 4.5),
        ('#FFFFFF', '#0C1B33', 4.5),
    ]
    for fg, bg, need in pairs:
        ratio = _contrast(fg, bg)
        if ratio < need:
            raise SystemExit(f'Contrast {ratio:.2f} for {fg} on {bg} is under {need}:1')
    return worst_text, worst_gold

class Site:
    def __init__(self, root, base, brand, groups, order, footer, css, notice, gsc=''):
        self.out = os.path.join(root, 'site')
        self.base = base.rstrip('/')
        self.brand = brand
        self.groups = groups
        self.order = order
        self.footer = footer
        self.css = css
        self.notice = notice
        self.gsc = gsc or ''
        self.pages = []
        self.indexable = []
        self.titles = {p: t for g, items in groups for p, t in items}
        self.titles['index.html'] = 'Home'
        self.summaries = {}
        self.read_next = {}
        self.aliases = {}
        self.checked = {}
        self._search_cache = None
        if os.path.exists(self.out):
            shutil.rmtree(self.out)
        os.makedirs(self.out)

    def _search_json(self):
        if self._search_cache is not None:
            return self._search_cache
        rows = [{"u": "/", "t": "Home", "s": self.summaries.get('index.html', ''), "g": "Home", "k": self.aliases.get('index.html', '')}]
        for g, items in self.groups:
            for p, t in items:
                rows.append({"u": href(p), "t": t, "s": self.summaries.get(p, ''), "g": g, "k": self.aliases.get(p, '')})
        self._search_cache = json.dumps(rows, ensure_ascii=True).replace('<', '\\u003c')
        return self._search_cache

    def page(self, path, title, desc, body, stage=None, kind='article', faqs=None, long_page=False, crumb=None):
        summary = self.summaries.get(path, '')
        if '<h1>' in body:
            body = body.replace('<h1>', '<h1 id="page-title">', 1)
        if summary and long_page and kind == 'article' and '<h1' in body:
            body = body.replace('</h1>', '</h1><div class="inshort"><p><strong>In short.</strong> ' + esc(summary) + '</p></div>', 1)
        seen = set()
        def addid(m):
            base = slug(m.group(1)) or 'section'
            n = base
            i = 2
            while n in seen:
                n = f'{base}-{i}'
                i += 1
            seen.add(n)
            return f'<h2 id="{n}">{m.group(1)}</h2>'
        body = re.sub(r'<h2>(.*?)</h2>', addid, body, flags=re.S)
        h2s = re.findall(r'<h2 id="([^"]*)">(.*?)</h2>', body)
        nav_bits = []
        for g, items in self.groups:
            links = []
            here = False
            for p, t in items:
                cur = ' aria-current="page"' if p == path else ''
                cls = ' class="is-current"' if p == path else ''
                if p == path:
                    here = True
                links.append(f'<a href="{href(p)}"{cls}{cur}>{esc(t)}</a>')
            mark = ' aria-current="true"' if here else ''
            nav_bits.append(f'<details class="grp{" has-current" if here else ""}"><summary{mark}>{esc(g)}</summary><div class="glinks">' + ''.join(links) + '</div></details>')
        nav = ''.join(nav_bits)
        url = None if kind == 'error' else canon_url(self.base, path)
        h1m = re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S)
        headline = H.unescape(re.sub(r'<[^>]+>', '', h1m.group(1))) if h1m else title
        checked_label, checked_iso = self.checked.get(path, (D, ISO))
        head, rest = _split_at_top_h2(body)
        toc = ''
        if len(h2s) >= 2:
            opened = ' open' if len(h2s) <= 8 else ''
            lis = ''.join(f'<li><a href="#{i}">{esc(H.unescape(re.sub("<[^>]+>", "", text)))}</a></li>' for i, text in h2s)
            toc = f'<nav class="toc" aria-label="On this page"><details class="toc-details"{opened}><summary>On this page</summary><ul>{lis}</ul></details>{TOC_BOOT}</nav>'
        plain = self.titles.get(path) or crumb or headline
        if path == 'index.html':
            crumbs = '<nav class="crumbs" aria-label="Breadcrumb"><ol><li><span aria-current="page">Home</span></li></ol></nav>'
        else:
            items_html = ['<li><a href="/">Home</a></li>']
            if stage:
                items_html.append(f'<li><a href="/#{slug(stage)}">{esc(stage)}</a></li>')
            items_html.append(f'<li><span aria-current="page">{esc(plain)}</span></li>')
            crumbs = '<nav class="crumbs" aria-label="Breadcrumb"><ol>' + ''.join(items_html) + '</ol></nav>'
        meta = f'<p class="meta"><span class="checked">Last checked: {esc(checked_label)}</span></p>'
        def step_link(target, kind_name):
            label = self.titles.get(target)
            if not label:
                return ''
            word = 'Previous' if kind_name == 'prev' else 'Next'
            return f'<a class="{kind_name}" href="{href(target)}"><span class="pn-k">{word}</span><span class="pn-t">{esc(label)}</span></a>'
        pn = ''
        if path in self.order:
            i = self.order.index(path)
            prev = step_link(self.order[i - 1], 'prev') if i > 0 else ''
            nxt = step_link(self.order[i + 1], 'next') if i + 1 < len(self.order) else ''
            if prev or nxt:
                pn = '<nav class="pn" aria-label="Previous and next">' + prev + nxt + '</nav>'
        rn_items = []
        for dest in self.read_next.get(path) or []:
            label = self.titles.get(dest) or self.titles.get(dest, '')
            if dest == 'index.html':
                label = 'Home'
            label = self.titles.get(dest)
            if not label:
                continue
            blurb = self.summaries.get(dest, '')
            blurb_html = f'<span class="ls">{esc(blurb)}</span>' if blurb else ''
            rn_items.append(f'<li><a class="jump" href="{href(dest)}"><span class="lt">{esc(label)}</span>{blurb_html}</a></li>')
        readnext = '<aside class="readnext" aria-labelledby="read-next"><h2 id="read-next">Read next</h2><ul>' + ''.join(rn_items) + '</ul></aside>' if rn_items else ''
        crumbs_ld = [{"@type": "ListItem", "position": 1, "name": "Home", "item": self.base + "/"}]
        if path != 'index.html':
            pos = 2
            if stage:
                crumbs_ld.append({"@type": "ListItem", "position": pos, "name": stage, "item": self.base + "/#" + slug(stage)})
                pos += 1
            item = {"@type": "ListItem", "position": pos, "name": plain}
            if kind != 'error' and url:
                item["item"] = url
            crumbs_ld.append(item)
        graph = []
        if kind == 'home':
            graph.append({"@type": "WebSite", "@id": self.base + "/#website", "name": self.brand, "url": self.base + "/", "description": desc, "publisher": {"@id": self.base + "/#organization"}})
            graph.append({"@type": "Organization", "@id": self.base + "/#organization", "name": self.brand, "url": self.base + "/", "logo": {"@type": "ImageObject", "url": self.base + "/apple-touch-icon.png"}})
        graph.append({"@type": "BreadcrumbList", "itemListElement": crumbs_ld})
        if kind != 'error':
            graph.append({"@type": "Article", "headline": title, "description": desc, "datePublished": checked_iso, "dateModified": checked_iso, "mainEntityOfPage": url, "image": self.base + "/og.png", "author": {"@type": "Organization", "name": self.brand, "url": self.base + "/"}, "publisher": {"@type": "Organization", "name": self.brand, "url": self.base + "/", "logo": {"@type": "ImageObject", "url": self.base + "/apple-touch-icon.png"}}})
        if faqs:
            graph.append({"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": H.unescape(re.sub(r'<[^>]+>', '', ahtml))}}
                for q, ahtml in faqs]})
        ld = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=True, separators=(',', ':')).replace('<', '\\u003c') + '</script>'
        robots = '<meta name="robots" content="noindex">' if kind == 'error' else ''
        canonical = '' if kind == 'error' else f'<link rel="canonical" href="{esc(url)}">'
        verify = f'<meta name="google-site-verification" content="{esc(self.gsc)}" />' if self.gsc else ''
        og_url = '' if kind == 'error' else f'<meta property="og:url" content="{esc(url)}">'
        times = '' if kind == 'error' else f'<meta property="article:published_time" content="{checked_iso}"><meta property="article:modified_time" content="{checked_iso}">'
        og_type = 'website' if kind != 'article' else 'article'
        image = self.base + '/og.png'
        layout_cls = 'layout has-toc' if toc else 'layout'
        brand_cur = ' aria-current="page"' if path == 'index.html' else ''
        h = f'''<!doctype html><html lang="en-US"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0C1B33"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}">{canonical}{robots}{verify}<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{esc(self.brand)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">{og_url}<meta property="og:image" content="{esc(image)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{esc(self.brand)}"><meta property="og:locale" content="en_US">{times}<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(desc)}"><meta name="twitter:image" content="{esc(image)}"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">{ld}<style>{self.css}</style><script defer src="/_vercel/insights/script.js"></script></head><body>
<a class="skip" href="#content">Skip to content</a>
<div id="head-slot"><header id="site-header"><div class="shell">
<a class="brand" href="/"{brand_cur}>{MARK}<span class="name"><span class="name-main">{esc(self.brand)}</span><span class="name-compact">Passport places</span><span class="name-sub">Independent guide. Not a government website.</span></span></a>
<button type="button" class="search-toggle" aria-expanded="false" aria-controls="site-search"><svg class="search-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15.5 15.5 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span class="search-toggle-text">Search</span></button>
<div class="search-wrap" id="site-search"><form class="sitesearch" role="search" action="/find/" method="get"><label for="q">Search this guide</label><input id="q" name="q" type="search" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"><button type="submit">Search</button></form><div id="search-results" class="search-results" hidden role="region" aria-live="polite" aria-label="Matching pages"></div></div>
<details class="menu"><summary>Topics</summary></details><nav id="site-nav" class="top" aria-label="Topics" tabindex="0">{nav}</nav>
<span class="nav-fade nav-fade-left" aria-hidden="true"></span><span class="nav-fade nav-fade-right" aria-hidden="true"></span><span class="nav-hint" aria-hidden="true"></span>
</div></header></div>
<main id="content" tabindex="-1"><div class="notice" role="note"><div class="shell"><p>{self.notice}</p></div></div><div class="shell">{crumbs}{meta}<article class="content" aria-labelledby="page-title"><div class="head-block">{head}</div><div class="{layout_cls}">{toc}<div class="rest">{rest}{pn}{readnext}</div></div></article></div></main>
<footer><div class="shell"><nav class="footnav" aria-label="About this guide"><a href="/find/">All pages</a><a href="/disclaimer/">Disclaimer</a></nav>{self.footer}</div></footer>
<script type="application/json" id="search-data">{self._search_json()}</script><script>{SEARCH_JS}</script><script>{DOCK_JS}</script></body></html>'''
        for bad in ('\u2014', '\u2013', '&mdash;', '&ndash;'):
            if bad in h:
                raise SystemExit(f'Em dash found in {path}')
        dest = os.path.join(self.out, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'w', encoding='utf-8').write(h)
        self.pages.append(path)
        if kind != 'error':
            self.indexable.append(path)

    def finish(self):
        text_ratio, gold_ratio = check_header_contrast(self.css)
        print(f'Header contrast: white text min {text_ratio:.2f}:1, gold focus min {gold_ratio:.2f}:1')
        if 'system-ui,-apple-system,"SegoeUI",Roboto,sans-serif' not in self.css.replace(' ', ''):
            raise SystemExit('Font stack missing from CSS')
        open(os.path.join(self.out, 'robots.txt'), 'w', encoding='utf-8').write(f"User-agent: *\nAllow: /\nSitemap: {self.base}/sitemap.xml\n")
        urls = ''.join(f'<url><loc>{canon_url(self.base, p)}</loc><lastmod>{self.checked.get(p, (D, ISO))[1]}</lastmod></url>\n' for p in sorted(self.indexable))
        open(os.path.join(self.out, 'sitemap.xml'), 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n')
        required = [
            'Independent guide. Not a government website.',
            'Last checked: ' + D,
            '/_vercel/insights/script.js',
            'For general information only.',
        ]
        if self.gsc:
            required.append(self.gsc)
        for path in self.pages:
            html = open(os.path.join(self.out, path), encoding='utf-8').read()
            for needle in required:
                if needle not in html:
                    raise SystemExit(f'Missing {needle} on {path}')
            if path != '404.html':
                if f'rel="canonical" href="{self.base}{href(path)}"' not in html:
                    raise SystemExit('Missing canonical on ' + path)
                if 'noindex' in html:
                    raise SystemExit('Unexpected noindex on ' + path)
            elif 'content="noindex"' not in html:
                raise SystemExit('404 should be noindex')
            if 'Read next' not in html:
                raise SystemExit('Missing Read next on ' + path)
        missing = _check_links(self.out, self.pages)
        if missing:
            raise SystemExit('Broken internal links:\n' + '\n'.join(missing))
        kept = [
            self.base + '/',
            self.base + '/child-under-16/',
            self.base + '/counties/broward/',
            self.base + '/counties/miami-dade/',
            self.base + '/counties/palm-beach/',
            self.base + '/disclaimer/',
            self.base + '/faq/',
            self.base + '/fees-and-documents/',
            self.base + '/walk-in-vs-appointment/',
            self.base + '/find/',
        ]
        sm = open(os.path.join(self.out, 'sitemap.xml'), encoding='utf-8').read()
        for loc in kept:
            if f'<loc>{loc}</loc>' not in sm:
                raise SystemExit('Sitemap missing ' + loc)

def _split_at_top_h2(body):
    """Split before the first h2 that is not nested, so a list can keep its own headings."""
    tag_re = re.compile(r'<(/?)([a-zA-Z0-9]+)?([^>]*)>')
    void = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
    depth = 0
    i = 0
    n = len(body)
    while i < n:
        if body[i] != '<':
            i += 1
            continue
        m = tag_re.match(body, i)
        if not m:
            i += 1
            continue
        closing = m.group(1) == '/'
        name = (m.group(2) or '').lower()
        attrs = m.group(3) or ''
        if name == 'h2' and not closing and depth == 0:
            return body[:i], body[i:]
        if closing:
            if depth:
                depth -= 1
        elif name and name not in void and not attrs.rstrip().endswith('/'):
            depth += 1
        i = m.end()
    return body, ''

def _check_links(out, pages):
    missing = []
    for path in pages:
        html = open(os.path.join(out, path), encoding='utf-8').read()
        ids = set(re.findall(r'\bid="([^"]*)"', html))
        for href_v in re.findall(r'\bhref="([^"]*)"', html):
            if href_v.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                continue
            url, _, frag = href_v.partition('#')
            if url == '':
                if frag and frag not in ids:
                    missing.append(f'{path} -> {href_v}')
                continue
            if url.startswith('/'):
                rel = url.lstrip('/')
                target = 'index.html' if rel == '' else (rel + 'index.html' if rel.endswith('/') else rel)
            else:
                target = os.path.normpath(os.path.join(os.path.dirname(path), url)).replace('\\', '/')
            dest = os.path.join(out, target)
            if not os.path.isfile(dest):
                missing.append(f'{path} -> {href_v} (missing {target})')
                continue
            if frag:
                tids = set(re.findall(r'\bid="([^"]*)"', open(dest, encoding='utf-8').read()))
                if frag not in tids:
                    missing.append(f'{path} -> {href_v} (missing #{frag})')
    return missing
