import os,json,re,sys,math
from pathlib import Path
from datetime import datetime,timezone
from difflib import SequenceMatcher
import requests

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
KEY=os.getenv('YOUTUBE_API_KEY')
if not KEY: raise SystemExit('YOUTUBE_API_KEY is required')
BASE='https://www.googleapis.com/youtube/v3'
LANGS={
 'Telugu':['Telugu full movie official','Telugu full film official','తెలుగు పూర్తి సినిమా','Telugu full movie'],
 'Tamil':['Tamil full movie official','Tamil full film official','தமிழ் முழு திரைப்படம்','Tamil full movie'],
 'Kannada':['Kannada full movie official','Kannada full film official','ಕನ್ನಡ ಪೂರ್ಣ ಸಿನಿಮಾ','Kannada full movie'],
 'Malayalam':['Malayalam full movie official','Malayalam full film official','മലയാളം മുഴുവൻ സിനിമ','Malayalam full movie']}
BAD=re.compile(r'\b(trailer|teaser|song|songs|music|lyrics|clip|scene|interview|reaction|review|short|shorts|making|behind the scenes|promo|preview|episode|part\s*[12]|tv serial|news|fan edit|fanmade|mashup)\b',re.I)
GOOD=re.compile(r'\b(full movie|full film|complete movie|official movie|full length)\b',re.I)
GENRE_KEYS={'Action':['action','fight'],'Comedy':['comedy','funny'],'Drama':['drama'],'Romance':['romance','love'],'Thriller':['thriller'],'Crime':['crime'],'Horror':['horror'],'Mystery':['mystery'],'Family':['family'],'Adventure':['adventure'],'Historical':['historical','period'],'Biography':['biography','biopic'],'Fantasy':['fantasy'],'Sci-Fi':['sci-fi','science fiction'],'Musical':['musical'],'Sports':['sports'],'Social':['social message','social'],'Classic':['classic']}

def api(path,params):
 p=dict(params,key=KEY);r=requests.get(f'{BASE}/{path}',params=p,timeout=30);r.raise_for_status();return r.json()

def parse_iso(s):
 m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',s or '')
 return (int(m.group(1) or 0)*3600+int(m.group(2) or 0)*60+int(m.group(3) or 0)) if m else 0

def norm(s):return re.sub(r'[^\w\s]',' ',str(s).lower(),flags=re.UNICODE).strip()
def slug(s):return re.sub(r'[^a-z0-9]+','-',norm(s)).strip('-') or 'movie'
def year_from(text):
 m=re.search(r'\b(19\d{2}|20\d{2})\b',text or '');return int(m.group(1)) if m else None

def genres(title,desc):
 t=(title+' '+desc).lower();return [g for g,ks in GENRE_KEYS.items() if any(k in t for k in ks)]

def query(q,lang):
 data=api('search',{'part':'snippet','q':q,'type':'video','videoEmbeddable':'true','videoSyndicated':'true','maxResults':50,'order':'relevance','safeSearch':'none'})
 return [(x['id']['videoId'],x['snippet'],lang) for x in data.get('items',[])]

def main():
 candidates=[]
 for lang,qs in LANGS.items():
  for q in qs:candidates.extend(query(q,lang))
 ids=list(dict.fromkeys(x[0] for x in candidates)); items=[]
 for i in range(0,len(ids),50):
  v=api('videos',{'part':'snippet,contentDetails,status,statistics','id':','.join(ids[i:i+50])}).get('items',[])
  for x in v:
   title=x['snippet'].get('title','');desc=x['snippet'].get('description','');dur=parse_iso(x.get('contentDetails',{}).get('duration',''))
   if x.get('status',{}).get('privacyStatus')!='public' or not x.get('status',{}).get('embeddable'):continue
   if BAD.search(title):continue
   if dur<2700:continue
   if not GOOD.search(title) and len(title.split())<3:continue
   # map language from which discovery query matched; prefer exact native-language hints only when available
   matches=[c[2] for c in candidates if c[0]==x['id']];lang=matches[0] if matches else 'Unknown'
   if lang not in LANGS:continue
   thumbs=x['snippet'].get('thumbnails',{});thumb=(thumbs.get('maxres') or thumbs.get('standard') or thumbs.get('high') or thumbs.get('medium') or thumbs.get('default') or {}).get('url')
   st=x.get('statistics',{});views=int(st.get('viewCount',0));likes=int(st.get('likeCount',0))
   channel=x['snippet'].get('channelTitle') or 'Unknown';cid=x['snippet'].get('channelId')
   item={'id':x['id'],'title':title,'slug':slug(title),'youtubeVideoId':x['id'],'youtubeUrl':f"https://www.youtube.com/watch?v={x['id']}",'thumbnail':thumb,'language':lang,'creator':{'name':channel,'channelId':cid,'channelUrl':f'https://www.youtube.com/channel/{cid}' if cid else None},'description':desc,'metadata':{'year':year_from(title+' '+desc),'genre':genres(title,desc),'durationSeconds':dur},'statistics':{'views':views,'likes':likes},'publishedAt':x['snippet'].get('publishedAt'),'verification':{'status':'unknown','method':'youtube-metadata'},'algorithm':{'trendingScore':0,'recommendationScore':0}}
   items.append(item)
 # deduplicate by title/language/year/duration. Keep the strongest source as canonical and preserve alternates.
 clusters=[]
 for m in items:
  found=None
  for c in clusters:
   a=c[0];sim=SequenceMatcher(None,norm(a['title']),norm(m['title'])).ratio();
   if a['language']==m['language'] and sim>=0.90 and (not a['metadata']['year'] or not m['metadata']['year'] or a['metadata']['year']==m['metadata']['year']) and abs(a['metadata']['durationSeconds']-m['metadata']['durationSeconds'])<=300:found=c;break
  if found:found.append(m)
  else:clusters.append([m])
 out=[]
 for c in clusters:
  c.sort(key=lambda m:(m['verification']['status']=='verified',m['metadata']['durationSeconds'],m['statistics']['views']),reverse=True);m=c[0]
  if len(c)>1:m['sources']= [{'youtubeVideoId':z['youtubeVideoId'],'youtubeUrl':z['youtubeUrl'],'creator':z['creator'],'embeddable':True,'views':z['statistics']['views']} for z in c]
  views=m['statistics']['views'];likes=m['statistics']['likes'];age=max((datetime.now(timezone.utc)-datetime.fromisoformat(m['publishedAt'].replace('Z','+00:00'))).total_seconds()/86400,1) if m.get('publishedAt') else 3650
  freshness=100*math.exp(-age/120);eng=min(100,likes/max(views,1)*1000);pop=min(100,math.log10(max(views,1))*12)
  m['algorithm']['trendingScore']=round(.38*freshness+.27*eng+.25*pop+.10*(100 if m['verification']['status']=='verified' else 35),2)
  m['algorithm']['recommendationScore']=round(.45*pop+.25*eng+.20*freshness+.10*min(100,m['metadata']['durationSeconds']/60),2)
  out.append(m)
 out.sort(key=lambda m:m['algorithm']['trendingScore'],reverse=True)
 (DATA/'movies.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 channels={}
 for m in out:
  c=m['creator'];channels[c.get('channelId')]=c
 (DATA/'channels.json').write_text(json.dumps(list(channels.values()),ensure_ascii=False,indent=2),encoding='utf-8')
 (DATA/'languages.json').write_text(json.dumps({l:sum(m['language']==l for m in out) for l in LANGS},indent=2),encoding='utf-8')
 (DATA/'genres.json').write_text(json.dumps({g:sum(g in m['metadata'].get('genre',[]) for m in out) for g in GENRE_KEYS},indent=2),encoding='utf-8')
 (DATA/'trending.json').write_text(json.dumps(out[:30],ensure_ascii=False,indent=2),encoding='utf-8')
 (DATA/'featured.json').write_text(json.dumps(out[:12],ensure_ascii=False,indent=2),encoding='utf-8')
 stats={'totalMovies':len(out),'byLanguage':{l:sum(m['language']==l for m in out) for l in LANGS},'byYear':{},'byGenre':{g:sum(g in m['metadata'].get('genre',[]) for m in out) for g in GENRE_KEYS},'verifiedSources':sum(m['verification']['status']=='verified' for m in out),'unknownSources':sum(m['verification']['status']=='unknown' for m in out),'brokenSources':0,'latestUpdate':datetime.now(timezone.utc).isoformat(),'catalogGrowth':len(out)}
 for m in out:
  y=m['metadata'].get('year');
  if y:stats['byYear'][str(y)]=stats['byYear'].get(str(y),0)+1
 (DATA/'stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'Catalog: {len(out)} movies')
if __name__=='__main__':main()
