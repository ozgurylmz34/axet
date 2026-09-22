import sqlite3,json,sys
c=sqlite3.connect(sys.argv[1])
sid=c.execute("select id from sessions order by created_at desc limit 1").fetchone()[0]
n=int(sys.argv[2]) if len(sys.argv)>2 else 400
for role,parts,ts in c.execute("select role,parts,created_at from messages where session_id=? order by created_at, rowid",(sid,)):
  for p in json.loads(parts):
    t=p['type']; d=p.get('data',{})
    if t=='tool_call': print(f"[{ts}] CALL {d['name']}: {d['input'][:n]}")
    elif t=='tool_result': print(f"[{ts}] RESULT {d['name']}: {d.get('content','')[:n]!r}")
    elif t=='text' and role=='assistant': print(f"[{ts}] TEXT: {d['text'][:150]!r}")
