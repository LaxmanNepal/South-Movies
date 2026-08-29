import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
registry=json.loads((DATA/'official-channels.json').read_text(encoding='utf-8'))
movies=json.loads((DATA/'movies.json').read_text(encoding='utf-8'))
allowed={c.get('channelId') for c in registry if c.get('channelId')}
if not allowed:
    raise SystemExit('No verified channel IDs found in official-channels.json')
clean=[]
removed=[]
seen=set()
for movie in movies:
    cid=(movie.get('creator') or {}).get('channelId')
    vid=movie.get('youtubeVideoId') or movie.get('id')
    if cid not in allowed:
        removed.append({'id':vid,'channelId':cid,'title':movie.get('title')})
        continue
    if movie.get('dubbed') is not True or str(movie.get('audioLanguage','')).lower()!='hindi':
        removed.append({'id':vid,'channelId':cid,'title':movie.get('title'),'reason':'not-hindi-dubbed'})
        continue
    if vid in seen:
        continue
    seen.add(vid)
    clean.append(movie)
if len(clean)!=len(movies):
    (DATA/'movies.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Removed {len(movies)-len(clean)} catalog entries outside the verified Hindi-dubbed whitelist.')
else:
    print(f'Catalog whitelist passed: {len(clean)} entries.')
if not clean:
    raise SystemExit('Catalog validation left zero Hindi-dubbed movies')
