from __future__ import annotations
import hashlib, hmac, json, os, re, secrets, sqlite3, time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

ROOT=Path(__file__).resolve().parent.parent
DB=Path(os.getenv("ACE_DB_PATH","/data/acepresso.sqlite3"))
DB.parent.mkdir(parents=True,exist_ok=True)
HTTPS=os.getenv("ACE_HTTPS","1")=="1"
SESSION_AGE=30*86400
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)

@contextmanager
def db():
    c=sqlite3.connect(DB,timeout=20,isolation_level=None)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA busy_timeout=20000")
    try: yield c
    finally:c.close()

def password_hash(p):
    salt=secrets.token_bytes(16)
    return salt.hex()+":"+hashlib.scrypt(p.encode(),salt=salt,n=16384,r=8,p=1,maxmem=33554432).hex()

def password_valid(p,record):
    try:
        a,b=record.split(":")
        h=hashlib.scrypt(p.encode(),salt=bytes.fromhex(a),n=16384,r=8,p=1,maxmem=33554432)
        return hmac.compare_digest(h,bytes.fromhex(b))
    except (ValueError,TypeError):return False

def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def error(status,message):raise HTTPException(status_code=status,detail=message)

def initialize():
    with db() as c:
        c.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS cohorts(id INTEGER PRIMARY KEY,title TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY,cohort_id INTEGER NOT NULL REFERENCES cohorts(id),title TEXT NOT NULL,UNIQUE(cohort_id,title));
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,login TEXT NOT NULL UNIQUE,passhash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN('admin','leader','student')),group_id INTEGER REFERENCES groups(id),created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS invites(id INTEGER PRIMARY KEY,code_hash TEXT UNIQUE NOT NULL,group_id INTEGER NOT NULL REFERENCES groups(id),role TEXT NOT NULL CHECK(role IN('leader','student')),expires_at INTEGER NOT NULL,used_by INTEGER UNIQUE REFERENCES users(id),created_by INTEGER REFERENCES users(id),created_at INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS progress(user_id INTEGER PRIMARY KEY REFERENCES users(id),data TEXT NOT NULL,updated_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(student_id INTEGER NOT NULL REFERENCES users(id),reviewer_id INTEGER NOT NULL REFERENCES users(id),day INTEGER NOT NULL CHECK(day BETWEEN 1 AND 21),score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 15),comment TEXT NOT NULL,updated_at INTEGER NOT NULL,PRIMARY KEY(student_id,day));
        CREATE TABLE IF NOT EXISTS attempts(ip TEXT NOT NULL,at INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS attempts_ix ON attempts(ip,at);
        """)
        c.execute("INSERT OR IGNORE INTO cohorts(title) VALUES('第一期')")
        cohort=c.execute("SELECT id FROM cohorts WHERE title='第一期'").fetchone()["id"]
        c.execute("INSERT OR IGNORE INTO groups(cohort_id,title) VALUES(?,'A组')",(cohort,))
        admin=os.getenv("ACE_ADMIN_LOGIN","").strip().lower()
        password=os.getenv("ACE_ADMIN_PASSWORD","")
        if admin and password and len(password)>=12:
            if not c.execute("SELECT id FROM users WHERE role='admin'").fetchone():
                c.execute("INSERT INTO users(name,login,passhash,role,created_at) VALUES(?,?,?,'admin',?)",
                          ("课程管理员",admin,password_hash(password),int(time.time())))
initialize()

@app.middleware("http")
async def headers(req,call_next):
    response=await call_next(req)
    for k,v in {
      "Cache-Control":"no-store","X-Content-Type-Options":"nosniff",
      "X-Frame-Options":"DENY","Referrer-Policy":"no-referrer",
      "Permissions-Policy":"camera=(), microphone=(), geolocation=()"
    }.items():response.headers[k]=v
    if HTTPS:response.headers["Strict-Transport-Security"]="max-age=31536000"
    return response

def user(req,optional=False):
    cookie=req.cookies.get("ace_session")
    if cookie:
        with db() as c:
            found=c.execute("""SELECT u.* FROM sessions s JOIN users u ON s.user_id=u.id
              WHERE s.token_hash=? AND s.expires_at>?""",(digest(cookie),int(time.time()))).fetchone()
            if found:return dict(found)
    if optional:return None
    error(401,"请先登录")

def who(u):
    return {"id":u["id"],"name":u["name"],"role":u["role"],"group_id":u["group_id"]}

def cookie(response,uid):
    now=int(time.time());token=secrets.token_urlsafe(36)
    with db() as c:
        c.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                  (digest(token),uid,now+SESSION_AGE))
    response.set_cookie("ace_session",token,path="/",max_age=SESSION_AGE,
                        httponly=True,secure=HTTPS,samesite="lax")

async def payload(req,size=10000):
    origin=req.headers.get("origin")
    if origin:
        target=urlparse(origin); expected=urlparse(str(req.base_url))
        if (target.scheme,target.netloc)!=(expected.scheme,expected.netloc):
            error(403,"无效请求来源")
    if req.headers.get("content-type","").split(";")[0].lower()!="application/json":
        error(415,"需要JSON格式")
    b=await req.body()
    if len(b)>size:error(413,"提交内容过大")
    try:
        value=json.loads(b)
        if not isinstance(value,dict):raise ValueError
        return value
    except (ValueError,UnicodeDecodeError):error(400,"JSON格式不正确")

def limited(req):
    ip=(req.client.host if req.client else "unknown")[:100];now=int(time.time())
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        c.execute("DELETE FROM attempts WHERE at<?",(now-900,))
        n=c.execute("SELECT COUNT(*) AS n FROM attempts WHERE ip=?",(ip,)).fetchone()["n"]
        if n>=12:
            c.execute("COMMIT");error(429,"尝试过于频繁")
        c.execute("INSERT INTO attempts(ip,at) VALUES(?,?)",(ip,now))
        c.execute("COMMIT")

@app.get("/")
def index(req:Request):
    if user(req,True):return RedirectResponse("/study",status_code=303)
    return HTMLResponse((ROOT/"web"/"login.html").read_text("utf8"))

@app.get("/study")
def study(req:Request):
    user(req)
    return HTMLResponse((ROOT/"web"/"study.html").read_text("utf8"))

@app.get("/manage")
def manage(req:Request):
    u=user(req)
    if u["role"]!="admin":error(403,"仅管理员可以进入")
    return HTMLResponse((ROOT/"web"/"manage.html").read_text("utf8"))

@app.get("/teacher")
def teacher(req:Request):
    u=user(req)
    if u["role"] not in ("leader","admin"):error(403,"仅组长或管理员可以进入")
    return HTMLResponse((ROOT/"web"/"teacher.html").read_text("utf8"))

@app.get("/api/health")
def health():return {"status":"ok"}

@app.get("/api/me")
def me(req:Request):return who(user(req))

@app.post("/api/register")
async def register(req:Request):
    d=await payload(req,5000);limited(req)
    login=str(d.get("login","")).strip().lower()
    name=str(d.get("name","")).strip();pw=str(d.get("password",""))
    invite=str(d.get("invite","")).strip().upper()
    if not (re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,49}",login) and
            1<=len(name)<=50 and 10<=len(pw)<=128 and 10<=len(invite)<=70):
        error(400,"姓名、账号、密码或邀请码格式不正确")
    now=int(time.time())
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        record=c.execute("""SELECT * FROM invites WHERE code_hash=? AND revoked=0
                          AND used_by IS NULL AND expires_at>?""",(digest(invite),now)).fetchone()
        if not record:error(400,"邀请码无效、过期或已经使用")
        if c.execute("SELECT id FROM users WHERE login=?",(login,)).fetchone():
            error(409,"账号已被注册")
        try:
            cur=c.execute("INSERT INTO users(name,login,passhash,role,group_id,created_at) VALUES(?,?,?,?,?,?)",
                (name,login,password_hash(pw),record["role"],record["group_id"],now))
            uid=cur.lastrowid
            c.execute("UPDATE invites SET used_by=? WHERE id=?",(uid,record["id"]))
            c.execute("COMMIT")
        except sqlite3.IntegrityError:
            c.execute("ROLLBACK");error(409,"账号或邀请码已经使用")
    r=JSONResponse({"ok":True,"user":{"id":uid,"name":name,"role":record["role"],"group_id":record["group_id"]}})
    cookie(r,uid);return r

@app.post("/api/login")
async def login(req:Request):
    d=await payload(req,4000);limited(req)
    with db() as c:
        u=c.execute("SELECT * FROM users WHERE login=?",(str(d.get("login","")).strip().lower(),)).fetchone()
    if not u or not password_valid(str(d.get("password","")),u["passhash"]):
        error(401,"账号或密码不正确")
    r=JSONResponse({"ok":True,"user":who(u)})
    cookie(r,u["id"]);return r

@app.post("/api/logout")
async def logout(req:Request):
    await payload(req,200)
    raw=req.cookies.get("ace_session")
    if raw:
        with db() as c:c.execute("DELETE FROM sessions WHERE token_hash=?",(digest(raw),))
    r=JSONResponse({"ok":True});r.delete_cookie("ace_session",path="/");return r

@app.post("/api/change-password")
async def change_password(req:Request):
    u=user(req);d=await payload(req,3000)
    pw=str(d.get("old_password",""));new=str(d.get("new_password",""))
    if not password_valid(pw,u["passhash"]) or not 12<=len(new)<=128:
        error(400,"旧密码错误或新密码少于12位")
    with db() as c:c.execute("UPDATE users SET passhash=? WHERE id=?",(password_hash(new),u["id"]))
    return {"ok":True}

@app.get("/api/progress")
def get_progress(req:Request):
    u=user(req)
    with db() as c:
        row=c.execute("SELECT data,updated_at FROM progress WHERE user_id=?",(u["id"],)).fetchone()
        reviews=c.execute("SELECT day,score,comment,updated_at FROM reviews WHERE student_id=?",(u["id"],)).fetchall()
    d=json.loads(row["data"]) if row else {}
    d["reviews"]={str(r["day"]):{"score":r["score"],"feedback":r["comment"],
       "status":"pass" if r["score"]>=12 else "revise","updated_at":r["updated_at"]} for r in reviews}
    return {"data":d,"updated_at":row["updated_at"] if row else None}

@app.put("/api/progress")
async def progress(req:Request):
    u=user(req);d=await payload(req,350000)
    val=d.get("data")
    if not isinstance(val,dict):error(400,"记录格式错误")
    keys={"goals","read","activity","activityConfirmed","ratings","answers",
          "submitted","notes","noteConfirmed","exported","groupNotes","lastDay"}
    value={k:v for k,v in val.items() if k in keys}
    for k,v in value.items():
        if k!="lastDay" and not isinstance(v,dict):error(400,"记录字段类型错误")
    txt=json.dumps(value,ensure_ascii=False,separators=(",",":"))
    if len(txt.encode())>300000:error(413,"记录过大")
    with db() as c:c.execute("""INSERT INTO progress(user_id,data,updated_at) VALUES(?,?,?)
       ON CONFLICT(user_id) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at""",
       (u["id"],txt,int(time.time())))
    return {"ok":True}

@app.get("/api/admin/groups")
def groups(req:Request):
    u=user(req)
    if u["role"]!="admin":error(403,"管理员权限不足")
    with db() as c:
        rows=c.execute("""SELECT g.id,g.title,c.title AS cohort FROM groups g
            JOIN cohorts c ON c.id=g.cohort_id ORDER BY g.id""").fetchall()
    return {"groups":[dict(r) for r in rows]}

@app.post("/api/admin/groups")
async def add_group(req:Request):
    u=user(req)
    if u["role"]!="admin":error(403,"管理员权限不足")
    d=await payload(req,3000)
    cohort=str(d.get("cohort","第一期")).strip()[:50]
    title=str(d.get("title","")).strip()[:50]
    if not cohort or not title:error(400,"请输入名称")
    with db() as c:
        c.execute("INSERT OR IGNORE INTO cohorts(title) VALUES(?)",(cohort,))
        cid=c.execute("SELECT id FROM cohorts WHERE title=?",(cohort,)).fetchone()["id"]
        c.execute("INSERT OR IGNORE INTO groups(cohort_id,title) VALUES(?,?)",(cid,title))
        gid=c.execute("SELECT id FROM groups WHERE cohort_id=? AND title=?",(cid,title)).fetchone()["id"]
    return {"ok":True,"group_id":gid}

@app.post("/api/admin/invitations")
async def invitations(req:Request):
    u=user(req)
    if u["role"]!="admin":error(403,"管理员权限不足")
    d=await payload(req,2000)
    try:
        gid=int(d.get("group_id",0));days=int(d.get("valid_days",14));count=int(d.get("count",1))
    except (ValueError,TypeError):error(400,"邀请码参数错误")
    role=d.get("role","student")
    if role not in ("student","leader") or not 1<=days<=90 or not 1<=count<=30:
        error(400,"邀请码数量、期限或类型不正确")
    with db() as c:
        if not c.execute("SELECT id FROM groups WHERE id=?",(gid,)).fetchone():
            error(404,"小组不存在")
        now=int(time.time());codes=[]
        for _ in range(count):
            code="ACE-"+secrets.token_hex(10).upper()
            c.execute("""INSERT INTO invites(code_hash,group_id,role,expires_at,created_by,created_at)
                        VALUES(?,?,?,?,?,?)""",
                      (digest(code),gid,role,now+days*86400,u["id"],now))
            codes.append(code)
    return {"codes":codes,"role":role,"valid_days":days,"group_id":gid}

@app.get("/api/teacher/submissions")
def submissions(req:Request):
    u=user(req)
    if u["role"] not in ("leader","admin"):error(403,"需要组长权限")
    with db() as c:
        if u["role"]=="admin":
            students=c.execute("SELECT id,name,group_id FROM users WHERE role='student'").fetchall()
        else:
            students=c.execute("SELECT id,name,group_id FROM users WHERE role='student' AND group_id=?",(u["group_id"],)).fetchall()
        result=[]
        for st in students:
            row=c.execute("SELECT data,updated_at FROM progress WHERE user_id=?",(st["id"],)).fetchone()
            if not row:continue
            data=json.loads(row["data"]);submitted=data.get("submitted",{});answers=data.get("answers",{})
            for day in range(1,22):
                if submitted.get(str(day)) or submitted.get(day):
                    result.append({"student_id":st["id"],"student":st["name"],
                       "group_id":st["group_id"],"day":day,
                       "answers":answers.get(str(day),{}),"updated_at":row["updated_at"]})
    return {"submissions":result}

@app.post("/api/teacher/reviews")
async def add_review(req:Request):
    u=user(req)
    if u["role"] not in ("leader","admin"):error(403,"需要组长权限")
    d=await payload(req,5000)
    try:
        sid=int(d.get("student_id"));day=int(d.get("day"));score=int(d.get("score"))
    except (ValueError,TypeError):error(400,"批改数据错误")
    comment=str(d.get("comment","")).strip()
    if not 1<=day<=21 or not 0<=score<=15 or not 2<=len(comment)<=2000:
        error(400,"评分或评语格式错误")
    with db() as c:
        st=c.execute("SELECT group_id FROM users WHERE id=? AND role='student'",(sid,)).fetchone()
        if not st or (u["role"]!="admin" and st["group_id"]!=u["group_id"]):
            error(403,"只能批改本组学员")
        c.execute("""INSERT INTO reviews(student_id,reviewer_id,day,score,comment,updated_at)
            VALUES(?,?,?,?,?,?) ON CONFLICT(student_id,day)
            DO UPDATE SET reviewer_id=excluded.reviewer_id,score=excluded.score,
             comment=excluded.comment,updated_at=excluded.updated_at""",
             (sid,u["id"],day,score,comment,int(time.time())))
    return {"ok":True}
