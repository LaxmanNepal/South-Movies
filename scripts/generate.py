import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';OUT=ROOT
LANGS=['Telugu','Tamil','Kannada','Malayalam'];GENRES=['Action','Comedy','Drama','Romance','Thriller','Crime','Horror','Mystery','Family','Adventure','Historical','Biography','Fantasy','Sci-Fi','Musical','Sports','Social','Classic']
def read(n,d):
 try:return json.loads((DATA/n).read_text(encoding='utf-8'))
 except:return d
def safe(s):return re.sub(r'[^a-z0-9]+','-',str(s).lower()).strip('-') or 'item'
def shell(title,desc,canonical,script='',ld=''):
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#090a0f"><meta name="description" content="{desc[:160].replace(chr(34),'&quot;')}"><link rel="canonical" href="{canonical}"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc[:160]}"><meta property="og:type" content="website"><meta name="twitter:card" content="summary_large_image"><link rel="manifest" href="/manifest.json"><link rel="stylesheet" href="/assets/styles.css"><title>{title} — SOUTH MOVIES</title>{ld}</head><body><div id="app"></div><script>{script}</script><script src="/assets/app.js" defer></script></body></html>'''
def build():
 movies=read('movies.json',[])
 for d in ['movies','creators','languages','genres','search','my-list','telugu','tamil','kannada','malayalam']: (OUT/d).mkdir(parents=True,exist_ok=True)
 for m in movies:
  m['slug']=m.get('slug') or safe(m.get('title'));p=OUT/'movies'/m['slug'];p.mkdir(parents=True,exist_ok=True)
  ld={'@context':'https://schema.org','@type':'VideoObject','name':m.get('title'),'description':m.get('description'),'thumbnailUrl':m.get('thumbnail'),'uploadDate':m.get('publishedAt'),'embedUrl':f"https://www.youtube.com/embed/{m.get('youtubeVideoId')}"}
  (p/'index.html').write_text(shell(m.get('title','Movie'),m.get('description') or 'South Indian movie discovery.',f"/movies/{m['slug']}/",f'window.SOUTH_MOVIES={{pageType:"movie",movieId:{json.dumps(m.get("id"))},movieSlug:{json.dumps(m["slug"])}}};',f'<script type="application/ld+json">{json.dumps(ld,ensure_ascii=False)}</script>'),encoding='utf-8')
 for l in LANGS:
  p=OUT/l.lower();p.mkdir(exist_ok=True);(p/'index.html').write_text(shell(f'{l} Movies',f'Discover {l} movies on SOUTH MOVIES.',f'/{l.lower()}/',f'window.SOUTH_MOVIES={{pageType:"language",language:{json.dumps(l)}}};'),encoding='utf-8')
 seen={}
 for m in movies:
  c=m.get('creator') or {};cid=c.get('channelId');name=c.get('name') or 'Unknown'
  if not cid:continue
  s=safe(name);seen[cid]=(s,name,cid)
 for s,name,cid in seen.values():
  p=OUT/'creators'/s;p.mkdir(exist_ok=True);(p/'index.html').write_text(shell(f'{name} Movies',f'Movies from YouTube creator {name}.',f'/creators/{s}/',f'window.SOUTH_MOVIES={{pageType:"creator",creator:{json.dumps(name)},channelId:{json.dumps(cid)}}};'),encoding='utf-8')
 for g in GENRES:
  s=safe(g);p=OUT/'genres'/s;p.mkdir(parents=True,exist_ok=True);(p/'index.html').write_text(shell(f'{g} South Movies',f'{g} movies across South Indian cinema.',f'/genres/{s}/',f'window.SOUTH_MOVIES={{pageType:"genre",genre:{json.dumps(g)}}};'),encoding='utf-8')
 (OUT/'languages'/'index.html').write_text(shell('South Indian Languages','Telugu, Tamil, Kannada and Malayalam movies.','/languages/','window.SOUTH_MOVIES={pageType:"languages"};'),encoding='utf-8')
 (OUT/'search'/'index.html').write_text(shell('Search South Movies','Search South Indian movie titles, languages, genres and creators.','/search/','window.SOUTH_MOVIES={pageType:"search"};'),encoding='utf-8')
 (OUT/'my-list'/'index.html').write_text(shell('My List','Your locally saved SOUTH MOVIES watchlist.','/my-list/','window.SOUTH_MOVIES={pageType:"list"};'),encoding='utf-8')
 urls=['/','/movies/','/languages/','/search/','/my-list/']+[f'/{l.lower()}/' for l in LANGS]+[f'/genres/{safe(g)}/' for g in GENRES]+[f'/creators/{s}/' for s,_,_ in seen.values()]+[f"/movies/{m['slug']}/" for m in movies]
 (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{u}</loc></url>' for u in urls)+'</urlset>',encoding='utf-8')
 (OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n',encoding='utf-8')
if __name__=='__main__':build()
