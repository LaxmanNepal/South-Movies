# South Movies health check helper
import json,requests,sys
from pathlib import Path
movies=json.loads((Path(__file__).resolve().parents[1]/'data/movies.json').read_text())
for m in movies:
 r=requests.get('https://www.youtube.com/oembed',params={'url':m['youtubeUrl'],'format':'json'},timeout=12)
 if r.status_code!=200: raise SystemExit(f"broken source: {m['id']}")
print('health check passed')
