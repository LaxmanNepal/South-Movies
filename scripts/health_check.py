import json,requests,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
movies=json.loads((ROOT/'data/movies.json').read_text(encoding='utf-8'))
errors=[]
for m in movies:
 if m.get('dubbed') is not True or str(m.get('audioLanguage','')).lower()!='hindi':
  errors.append(f"not Hindi dubbed: {m.get('id')}")
  continue
 url=m.get('youtubeUrl')
 try:
  r=requests.get('https://www.youtube.com/oembed',params={'url':url,'format':'json'},timeout=12)
  if r.status_code!=200: errors.append(f"unavailable source ({r.status_code}): {m.get('id')}")
 except requests.RequestException as e:
  errors.append(f"source check failed: {m.get('id')} ({e})")
if errors:
 print('\n'.join(errors));raise SystemExit(f'Health check failed: {len(errors)} issue(s)')
print(f'Health check passed: {len(movies)} Hindi-dubbed sources available.')
