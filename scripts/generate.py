import json,re,shutil
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=ROOT
LANGS=['Telugu','Tamil','Kannada','Malayalam']
GENRES=['Action','Comedy','Drama','Romance','Thriller','Crime','Horror','Mystery','Family','Adventure','Historical','Biography','Fantasy','Sci-Fi','Musical','Sports','Social','Classic']

def read(name,default):
 p=DATA/name
 try:return json.loads(p.read_text(encoding='utf-8'))
 except:return default

def safe(s):return re.sub(r'[^a-z0-9]+','-',str(s).lower()).strip('-') or 'movie'

def shell(title,desc,canonical,body,extra=''):
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#090a0f"><meta name="description" content="{desc}"><link rel="canonical" href="{canonical}"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:type" content="website"><meta name="twitter:card" content="summary_large_image"><link rel="manifest" href="/manifest.json"><link rel="stylesheet" href="/assets/styles.css"><title>{title} — SOUTH MOVIES</title>{extra}</head><body><div id="app">{body}</div><script src="/assets/app.js" defer></script></body></html>'''

def movie_page(m):
 mid=json.dumps(m.get('id')); ms=json.dumps(m.get('slug') or safe(m.get('title'))); desc=(m.get('description') or 'Discover this South Indian movie through its original YouTube source.')[:160].replace('"','&quot;')
 ld={'@context':'https://schema.org','@type':'VideoObject','name':m.get('title'),'description':m.get('description'),'thumbnailUrl':m.get('thumbnail'),'uploadDate':m.get('publishedAt'),'embedUrl':f"https://www.youtube.com/embed/{m.get('youtubeVideoId')}",'publisher':{'@type':'Organization','name':m.get('creator',{}).get('name') or 'Unknown'}}
 body='<div id="app"></div>'
 return shell(m.get('title','Movie'),desc,f"/movies/{m.get('slug') or safe(m.get('title'))}/",body,f'<script type="application/ld+json">{json.dumps(ld,ensure_ascii=False)}</script><script>window.SOUTH_MOVIES={{pageType:"movie",movieId:{mid},movieSlug:{ms}}};</script>')

def simple_page(title,desc,ptype):
 return shell(title,desc,'/', '<div id="app"></div>',f'<script>window.SOUTH_MOVIES={{pageType:"{ptype}"}};</script>')

def build():
 movies=read('movies.json',[])
 for p in [OUT/'movies',OUT/'creators',OUT/'telugu',OUT/'tamil',OUT/'kannada',OUT/'malayalam',OUT/'languages',OUT/'search',OUT/'my-list',OUT/'genres']:
  p.mkdir(parents=True,exist_ok=True)
 for m in movies:
  s=m.get('slug') or safe(m.get('title'));m['slug']=s
  p=OUT/'movies'/s;p.mkdir(parents=True,exist_ok=True);(p/'index.html').write_text(movie_page(m),encoding='utf-8')
 for l in LANGS:
  p=OUT/l.lower();p.mkdir(exist_ok=True);(p/'index.html').write_text(simple_page(f'{l} Movies',f'Discover {l} movies on SOUTH MOVIES.','language'),encoding='utf-8')
 for c in {m.get('creator',{}).get('channelId'):m.get('creator',{}) for m in movies if m.get('creator',{}).get('channelId')}.values():
  s=safe(c.get('name') or c.get('channelId'));p=OUT/'creators'/s;p.mkdir(exist_ok=True);(p/'index.html').write_text(simple_page(f"{c.get('name','Creator')} Movies",'Movies from this YouTube creator.','creator'),encoding='utf-8')
 (OUT/'languages'/'index.html').write_text(simple_page('South Indian Languages','Telugu, Tamil, Kannada and Malayalam movies.','languages'),encoding='utf-8')
 (OUT/'search'/'index.html').write_text(simple_page('Search South Movies','Search South Indian movie titles, languages, genres and creators.','search'),encoding='utf-8')
 (OUT/'my-list'/'index.html').write_text(simple_page('My List','Your locally saved SOUTH MOVIES watchlist.','list'),encoding='utf-8')
 for g in GENRES:
  p=OUT/'genres'/safe(g);p.mkdir(parents=True,exist_ok=True);(p/'index.html').write_text(simple_page(f'{g} South Movies',f'{g} movies across South Indian cinema.','genre'),encoding='utf-8')
 urls=['/','/movies/','/languages/','/search/','/my-list/']+[f'/{l.lower()}/' for l in LANGS]+[f'/genres/{safe(g)}/' for g in GENRES]
 urls += [f"/movies/{m.get('slug') or safe(m.get('title'))}/" for m in movies]
 (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{u}</loc></url>' for u in urls)+'</urlset>',encoding='utf-8')
 (OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n',encoding='utf-8')

if __name__=='__main__':build()
