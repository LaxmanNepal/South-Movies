import os,json,re,math,time
from pathlib import Path
from datetime import datetime,timezone
from difflib import SequenceMatcher
import requests
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
KEY=os.getenv('YOUTUBE_API_KEY')
if not KEY: raise SystemExit('YOUTUBE_API_KEY is required')
BASE='https://www.googleapis.com/youtube/v3'; MAX_PAGES_PER_CHANNEL=int(os.getenv('MAX_PAGES_PER_CHANNEL','10'))
LANGS={'Telugu':['telugu','तेलुगु'],'Tamil':['tamil','तमिल'],'Kannada':['kannada','कन्नड़'],'Malayalam':['malayalam','मलयालम']}
BAD=re.compile(r'\b(trailer|teaser|song|songs|music video|lyrics?|clip|scene|interview|reaction|review|shorts?|making|behind the scenes|promo|preview|episode|part\s*(?:1|2|one|two)|tv serial|news|fan edit|fanmade|mashup|status video)\b',re.I)
DUB=re.compile(r'(hindi\s*dub(?:bed|bing)?|dubbed\s*in\s*hindi|hindi\s*version|हिंदी\s*(डब|डब्ड|में\s*डब)|हिंदी\s*वर्जन)',re.I)
GOOD=re.compile(r'\b(full movie|full film|complete movie|complete film|official movie|official full|full length|movie|film)\b',re.I)
def api(path,params,retries=6):
    for attempt in range(retries):
        try:
            r=requests.get(f'{BASE}/{path}',params={**params,'key':KEY},timeout=30)
            if r.status_code in (429,500,502,503,504):
                wait=min(45,2**attempt); print(f'YouTube {r.status_code}; retrying in {wait}s'); time.sleep(wait); continue
            r.raise_for_status(); return r.json()
        except requests.RequestException as e:
            if attempt==retries-1: raise
            wait=min(45,2**attempt); print(f'YouTube request error: {e}; retrying in {wait}s'); time.sleep(wait)
    raise RuntimeError('YouTube API request failed')
def parse_iso(s):
    m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',s or '')
    return int(m.group(1) or 0)*3600+int(m.group(2) or 0)*60+int(m.group(3) or 0) if m else 0
def norm(s): return re.sub(r'[^\w\s]',' ',str(s).lower(),flags=re.UNICODE).strip()
def slug(s): return re.sub(r'[^a-z0-9]+','-',norm(s)).strip('-') or 'movie'
def year_from(text):
    m=re.search(r'\b(19\d{2}|20\d{2})\b',text or ''); return int(m.group(1)) if m else None
def resolve_channels(channels):
    out=[]
    for c in channels:
        cid=c.get('channelId')
        if not cid and c.get('handle'):
            try:
                d=api('channels',{'part':'id,contentDetails,snippet','forHandle':c['handle'].lstrip('@')})
                if d.get('items'): c['channelId']=d['items'][0]['id']; cid=c['channelId']
            except requests.RequestException as e: print(f'Channel resolve failed: {c.get("name")}: {e}')
        if cid: out.append(c)
        else: print(f'Skipping unresolved official channel: {c.get("name")}')
    return out
def channel_videos(channel):
    d=api('channels',{'part':'contentDetails','id':channel['channelId']})
    if not d.get('items'): return []
    uploads=d['items'][0]['contentDetails']['relatedPlaylists']['uploads']; videos=[]; token=None
    for page in range(MAX_PAGES_PER_CHANNEL):
        p={'part':'contentDetails,snippet','playlistId':uploads,'maxResults':50}
        if token:p['pageToken']=token
        d=api('playlistItems',p)
        videos += [x.get('contentDetails',{}).get('videoId') for x in d.get('items',[]) if x.get('contentDetails',{}).get('videoId')]
        token=d.get('nextPageToken')
        if not token: break
    return list(dict.fromkeys(videos))
def detect_language(text,channel):
    hits=[l for l,terms in LANGS.items() if any(re.search(r'\b'+re.escape(t)+r'\b',text,re.I) for t in terms)]
    if hits:return hits[0]
    scope=str(channel.get('scope','')).lower()
    for l in LANGS:
        if l.lower() in scope:return l
    return 'South Indian'
def main():
    rp=DATA/'official-channels.json'
    if not rp.exists(): raise SystemExit('data/official-channels.json is required')
    registry=json.loads(rp.read_text(encoding='utf-8'))
    if not isinstance(registry,list) or not registry: raise SystemExit('official-channels.json must contain a non-empty array')
    official=resolve_channels(registry); verified={c['channelId'] for c in official}
    if not verified: raise SystemExit('No resolvable official channel IDs')
    candidates=[]; channel_by_id={c['channelId']:c for c in official}
    for c in official:
        for vid in channel_videos(c): candidates.append((vid,c['channelId']))
    candidates=list(dict.fromkeys(candidates)); print(f'Collected {len(candidates)} videos from {len(verified)}/{len(registry)} whitelisted channels')
    items=[]; rejected={'not_public_or_embeddable':0,'bad_content':0,'too_short':0,'not_hindi_dubbed':0,'not_movie':0,'unknown':0}
    for i in range(0,len(candidates),50):
        for x in api('videos',{'part':'snippet,contentDetails,status,statistics','id':','.join(v for v,_ in candidates[i:i+50])}).get('items',[]):
            sn=x.get('snippet',{}); title=sn.get('title',''); desc=sn.get('description',''); text=title+' '+desc; cid=sn.get('channelId'); dur=parse_iso(x.get('contentDetails',{}).get('duration',''))
            if cid not in verified or x.get('status',{}).get('privacyStatus')!='public' or not x.get('status',{}).get('embeddable'): rejected['not_public_or_embeddable']+=1; continue
            if BAD.search(title): rejected['bad_content']+=1; continue
            if dur<2700: rejected['too_short']+=1; continue
            if not DUB.search(text): rejected['not_hindi_dubbed']+=1; continue
            if not GOOD.search(title): rejected['not_movie']+=1; continue
            channel=channel_by_id[cid]; lang=detect_language(text,channel)
            thumbs=sn.get('thumbnails',{}); thumb=(thumbs.get('maxres') or thumbs.get('standard') or thumbs.get('high') or thumbs.get('medium') or thumbs.get('default') or {}).get('url'); st=x.get('statistics',{}); views=int(st.get('viewCount',0)); likes=int(st.get('likeCount',0)); channel_name=sn.get('channelTitle') or channel.get('name','Unknown')
            items.append({'id':x['id'],'title':title,'slug':slug(title),'youtubeVideoId':x['id'],'youtubeUrl':f'https://www.youtube.com/watch?v={x["id"]}','thumbnail':thumb,'language':lang,'audioLanguage':'Hindi','dubbed':True,'creator':{'name':channel_name,'channelId':cid,'channelUrl':f'https://www.youtube.com/channel/{cid}'},'description':desc,'metadata':{'year':year_from(text),'genre':[],'durationSeconds':dur},'statistics':{'views':views,'likes':likes},'publishedAt':sn.get('publishedAt'),'verification':{'status':'verified','method':'official-channel-whitelist'},'algorithm':{'trendingScore':0,'recommendationScore':0}})
    clusters=[]
    for m in items:
        found=next((c for c in clusters if c[0]['language']==m['language'] and SequenceMatcher(None,norm(c[0]['title']),norm(m['title'])).ratio()>=.88 and (not c[0]['metadata']['year'] or not m['metadata']['year'] or c[0]['metadata']['year']==m['metadata']['year']) and abs(c[0]['metadata']['durationSeconds']-m['metadata']['durationSeconds'])<=360),None)
        (found.append(m) if found else clusters.append([m]))
    out=[]
    for c in clusters:
        c.sort(key=lambda m:m['statistics']['views'],reverse=True); m=c[0]; views=m['statistics']['views']; likes=m['statistics']['likes']; pub=m.get('publishedAt'); age=max((datetime.now(timezone.utc)-datetime.fromisoformat(pub.replace('Z','+00:00'))).total_seconds()/86400,1) if pub else 3650; freshness=100*math.exp(-age/120); eng=min(100,likes/max(views,1)*1000); pop=min(100,math.log10(max(views,1))*12); m['algorithm']['trendingScore']=round(.38*freshness+.27*eng+.25*pop+10,2); m['algorithm']['recommendationScore']=round(.45*pop+.25*eng+.20*freshness+10,2); out.append(m)
    out.sort(key=lambda m:m['algorithm']['trendingScore'],reverse=True)
    for name,obj in [('movies.json',out),('trending.json',out[:30]),('featured.json',out[:12])]: (DATA/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    channels={m['creator']['channelId']:m['creator'] for m in out}; (DATA/'channels.json').write_text(json.dumps(list(channels.values()),ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); (DATA/'languages.json').write_text(json.dumps({l:sum(m['language']==l for m in out) for l in list(LANGS)+['South Indian']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); (DATA/'genres.json').write_text('{}\n',encoding='utf-8')
    stats={'totalMovies':len(out),'officialChannels':len(official),'registryChannels':len(registry),'unresolvedChannels':len(registry)-len(official),'videosScanned':len(candidates),'rejections':rejected,'byLanguage':{l:sum(m['language']==l for m in out) for l in list(LANGS)+['South Indian']},'byYear':{},'byGenre':{},'verifiedSources':len(out),'probableSources':0,'unknownSources':0,'brokenSources':0,'latestUpdate':datetime.now(timezone.utc).isoformat(),'catalogGrowth':len(out),'languageScope':'South Indian cinema','audioScope':'Hindi dubbed only','sourcePolicy':'Verified channel ID whitelist + channel uploads only'}
    for m in out:
        y=m['metadata'].get('year')
        if y: stats['byYear'][str(y)]=stats['byYear'].get(str(y),0)+1
    (DATA/'stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); rp.write_text(json.dumps(official,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Catalog: {len(out)} Hindi-dubbed South movies from {len(official)} verified channels; scanned {len(candidates)} videos')
    if not out: raise SystemExit('No qualifying Hindi-dubbed movies found; refusing to publish an empty catalog')
if __name__=='__main__': main()
