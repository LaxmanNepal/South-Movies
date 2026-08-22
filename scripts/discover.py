import os,json,re,math
from pathlib import Path
from datetime import datetime,timezone
from difflib import SequenceMatcher
import requests
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
KEY=os.getenv('YOUTUBE_API_KEY')
if not KEY: raise SystemExit('YOUTUBE_API_KEY is required')
BASE='https://www.googleapis.com/youtube/v3'
LANGS={
 'Telugu':['Telugu movie Hindi dubbed full movie','Telugu Hindi dubbed full movie','Telugu full movie Hindi dubbed','तेलुगु हिंदी डब्ड फुल मूवी'],
 'Tamil':['Tamil movie Hindi dubbed full movie','Tamil Hindi dubbed full movie','Tamil full movie Hindi dubbed','तमिल हिंदी डब्ड फुल मूवी'],
 'Kannada':['Kannada movie Hindi dubbed full movie','Kannada Hindi dubbed full movie','Kannada full movie Hindi dubbed','कन्नड़ हिंदी डब्ड फुल मूवी'],
 'Malayalam':['Malayalam movie Hindi dubbed full movie','Malayalam Hindi dubbed full movie','Malayalam full movie Hindi dubbed','मलयालम हिंदी डब्ड फुल मूवी']}
BAD=re.compile(r'\b(trailer|teaser|song|songs|music video|lyrics|lyric|clip|scene|interview|reaction|review|short|shorts|making|behind the scenes|promo|preview|episode|part\s*(?:1|2|one|two)|tv serial|news|fan edit|fanmade|mashup|status video)\b',re.I)
DUB=re.compile(r'(hindi\s*dub(?:bed|bing)?|dubbed\s*in\s*hindi|hindi\s*version|हिंदी\s*(डब|डब्ड|में\s*डब)|हिंदी\s*वर्जन)',re.I)
GOOD=re.compile(r'\b(full movie|full film|complete movie|complete film|official movie|official full|full length)\b',re.I)

def api(path,params):
 r=requests.get(f'{BASE}/{path}',params={**params,'key':KEY},timeout=30);r.raise_for_status();return r.json()
def parse_iso(s):
 m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',s or '')
 return int(m.group(1) or 0)*3600+int(m.group(2) or 0)*60+int(m.group(3) or 0) if m else 0
def norm(s):return re.sub(r'[^\w\s]',' ',str(s).lower(),flags=re.UNICODE).strip()
def slug(s):return re.sub(r'[^a-z0-9]+','-',norm(s)).strip('-') or 'movie'
def year_from(text):
 m=re.search(r'\b(19\d{2}|20\d{2})\b',text or '');return int(m.group(1)) if m else None
def verification(channel,description,channel_id,verified):
 if channel_id in verified:return {'status':'verified','method':'manual'}
 text=(channel+' '+description).lower()
 if 'official' in channel.lower() and any(k in text for k in ['movie','film','production','distributor','entertainment']):return {'status':'probable','method':'youtube-metadata'}
 return {'status':'unknown','method':'youtube-metadata'}
def main():
 verified=set(json.loads((DATA/'verified-channels.json').read_text()) if (DATA/'verified-channels.json').exists() else [])
 candidates=[]
 for lang,qs in LANGS.items():
  for q in qs:
   d=api('search',{'part':'snippet','q':q,'type':'video','videoEmbeddable':'true','videoDuration':'long','maxResults':50,'order':'relevance','safeSearch':'none','regionCode':'IN'})
   candidates += [(x['id']['videoId'],lang) for x in d.get('items',[]) if x.get('id',{}).get('videoId')]
 match={}
 for vid,lang in candidates:match.setdefault(vid,[]).append(lang)
 ids=list(match);items=[]
 for i in range(0,len(ids),50):
  for x in api('videos',{'part':'snippet,contentDetails,status,statistics','id':','.join(ids[i:i+50])}).get('items',[]):
   sn=x.get('snippet',{});title=sn.get('title','');desc=sn.get('description','');text=title+' '+desc;dur=parse_iso(x.get('contentDetails',{}).get('duration',''))
   if x.get('status',{}).get('privacyStatus')!='public' or not x.get('status',{}).get('embeddable'):continue
   if BAD.search(title) or dur<2700 or not GOOD.search(title) or not DUB.search(text):continue
   lang=match.get(x['id'],['Unknown'])[0]
   if lang not in LANGS:continue
   thumbs=sn.get('thumbnails',{});thumb=(thumbs.get('maxres') or thumbs.get('standard') or thumbs.get('high') or thumbs.get('medium') or thumbs.get('default') or {}).get('url')
   st=x.get('statistics',{});views=int(st.get('viewCount',0));likes=int(st.get('likeCount',0));channel=sn.get('channelTitle') or 'Unknown';cid=sn.get('channelId')
   items.append({'id':x['id'],'title':title,'slug':slug(title),'youtubeVideoId':x['id'],'youtubeUrl':f'https://www.youtube.com/watch?v={x["id"]}','thumbnail':thumb,'language':lang,'audioLanguage':'Hindi','dubbed':True,'creator':{'name':channel,'channelId':cid,'channelUrl':f'https://www.youtube.com/channel/{cid}' if cid else None},'description':desc,'metadata':{'year':year_from(text),'genre':[],'durationSeconds':dur},'statistics':{'views':views,'likes':likes},'publishedAt':sn.get('publishedAt'),'verification':verification(channel,desc,cid,verified),'algorithm':{'trendingScore':0,'recommendationScore':0}})
 clusters=[]
 for m in items:
  found=None
  for c in clusters:
   a=c[0];sim=SequenceMatcher(None,norm(a['title']),norm(m['title'])).ratio()
   if a['language']==m['language'] and sim>=.88 and (not a['metadata']['year'] or not m['metadata']['year'] or a['metadata']['year']==m['metadata']['year']) and abs(a['metadata']['durationSeconds']-m['metadata']['durationSeconds'])<=360:found=c;break
  (found.append(m) if found else clusters.append([m]))
 out=[]
 for c in clusters:
  c.sort(key=lambda m:(m['verification']['status']=='verified',m['verification']['status']=='probable',m['statistics']['views']),reverse=True);m=c[0]
  if len(c)>1:m['sources']=[{'youtubeVideoId':z['youtubeVideoId'],'youtubeUrl':z['youtubeUrl'],'creator':z['creator'],'embeddable':True,'views':z['statistics']['views'],'verification':z['verification']} for z in c]
  views=m['statistics']['views'];likes=m['statistics']['likes'];pub=m.get('publishedAt');age=max((datetime.now(timezone.utc)-datetime.fromisoformat(pub.replace('Z','+00:00'))).total_seconds()/86400,1) if pub else 3650
  freshness=100*math.exp(-age/120);eng=min(100,likes/max(views,1)*1000);pop=min(100,math.log10(max(views,1))*12);quality={'verified':100,'probable':70,'unknown':35}.get(m['verification']['status'],35)
  m['algorithm']['trendingScore']=round(.38*freshness+.27*eng+.25*pop+.10*quality,2);m['algorithm']['recommendationScore']=round(.45*pop+.25*eng+.20*freshness+.10*quality,2);out.append(m)
 out.sort(key=lambda m:m['algorithm']['trendingScore'],reverse=True)
 for name,obj in [('movies.json',out),('trending.json',out[:30]),('featured.json',out[:12])]: (DATA/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
 channels={m['creator'].get('channelId'):m['creator'] for m in out};(DATA/'channels.json').write_text(json.dumps(list(channels.values()),ensure_ascii=False,indent=2),encoding='utf-8')
 (DATA/'languages.json').write_text(json.dumps({l:sum(m['language']==l for m in out) for l in LANGS},ensure_ascii=False,indent=2),encoding='utf-8')
 (DATA/'genres.json').write_text(json.dumps({},indent=2),encoding='utf-8')
 stats={'totalMovies':len(out),'byLanguage':{l:sum(m['language']==l for m in out) for l in LANGS},'byYear':{},'byGenre':{},'verifiedSources':sum(m['verification']['status']=='verified' for m in out),'probableSources':sum(m['verification']['status']=='probable' for m in out),'unknownSources':sum(m['verification']['status']=='unknown' for m in out),'brokenSources':0,'latestUpdate':datetime.now(timezone.utc).isoformat(),'catalogGrowth':len(out),'languageScope':'South Indian cinema','audioScope':'Hindi dubbed only'}
 for m in out:
  y=m['metadata'].get('year')
  if y:stats['byYear'][str(y)]=stats['byYear'].get(str(y),0)+1
 (DATA/'stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8');print(f'Catalog: {len(out)} Hindi-dubbed South movies')
if __name__=='__main__':main()
