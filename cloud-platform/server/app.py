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
        CREATE TABLE IF NOT EXISTS leader_password_resets(
          id INTEGER PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES users(id),
          code_hash TEXT NOT NULL UNIQUE,
          issued_by INTEGER NOT NULL REFERENCES users(id),
          expires_at INTEGER NOT NULL,
          used_at INTEGER,
          created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS leader_reset_user_ix ON leader_password_resets(user_id,expires_at);
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

# One-time, idempotent enrollment provisioning. Secrets and plain invitation codes
# are supplied through Railway environment variables, never committed to GitHub.
def apply_enrollment_batch():
    batch=os.getenv("ACE_ENROLL_BATCH","").strip()
    seed=os.getenv("ACE_ENROLL_SEED","").strip()
    admin_verifier=os.getenv("ACE_ENROLL_ADMIN_VERIFIER","").strip()
    if not (batch and seed and admin_verifier):
        return
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,90}",batch) or not re.fullmatch(r"[a-fA-F0-9]{64}",seed):
        raise RuntimeError("Enrollment configuration is invalid")
    if not re.fullmatch(r"[a-fA-F0-9]{32}:[a-fA-F0-9]{128}",admin_verifier):
        raise RuntimeError("Admin credential verifier is invalid")
    key=bytes.fromhex(seed)
    now=int(time.time())
    cohort_name="ACEpresso首期·2026年11月"
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        c.execute("""CREATE TABLE IF NOT EXISTS enrollment_batches
                     (batch_id TEXT PRIMARY KEY, applied_at INTEGER NOT NULL,
                      leader_count INTEGER NOT NULL, student_count INTEGER NOT NULL)""")
        if c.execute("SELECT 1 FROM enrollment_batches WHERE batch_id=?",(batch,)).fetchone():
            c.execute("COMMIT")
            print("ACEpresso enrollment batch already applied",flush=True)
            return
        admin_login=os.getenv("ACE_ADMIN_LOGIN","ace-director").strip().lower()
        admin=c.execute("SELECT id FROM users WHERE role='admin' AND login=?",(admin_login,)).fetchone()
        if not admin:
            c.execute("ROLLBACK")
            raise RuntimeError("Existing ACEpresso administrator not found")
        c.execute("INSERT OR IGNORE INTO cohorts(title) VALUES(?)",(cohort_name,))
        cid=c.execute("SELECT id FROM cohorts WHERE title=?",(cohort_name,)).fetchone()["id"]
        gids=[]
        for letter in "ABCDEFGH":
            title=letter+"组"
            c.execute("INSERT OR IGNORE INTO groups(cohort_id,title) VALUES(?,?)",(cid,title))
            row=c.execute("SELECT id FROM groups WHERE cohort_id=? AND title=?",(cid,title)).fetchone()
            gids.append(row["id"])
        def make_invite(role,number,gid):
            digest_part=hmac.new(key,f"{batch}:{role}:{number}".encode(),hashlib.sha256).hexdigest().upper()[:24]
            code=f"ACE-{role[0].upper()}{number:02d}-{digest_part}"
            c.execute("""INSERT INTO invites
                         (code_hash,group_id,role,expires_at,used_by,created_by,created_at,revoked)
                         VALUES(?,?,?,?,NULL,?,?,0)""",
                      (digest(code),gid,role,now+60*86400,admin["id"],now))
        for num,gid in enumerate(gids,1):
            make_invite("leader",num,gid)
        for num in range(1,61):
            make_invite("student",num,gids[(num-1)%8])
        c.execute("UPDATE users SET passhash=? WHERE id=?",(admin_verifier,admin["id"]))
        c.execute("DELETE FROM sessions WHERE user_id=?",(admin["id"],))
        c.execute("INSERT INTO enrollment_batches VALUES(?,?,8,60)",(batch,now))
        c.execute("COMMIT")
    print("ACEpresso enrollment batch applied: 8 leader invites, 60 student invites, 8 groups; admin credential rotated",flush=True)

apply_enrollment_batch()

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
        target=urlparse(origin)
        # Railway terminates HTTPS before forwarding to the ASGI app. The
        # internal request URL may be http://, so compare against an explicit
        # externally configured origin rather than the proxy-side base_url.
        configured=os.getenv("ACE_PUBLIC_ORIGIN","").strip()
        expected_origins=[urlparse(v.strip()) for v in configured.split(",") if v.strip()] if configured else [urlparse(str(req.base_url))]
        if (target.scheme,target.netloc) not in {(o.scheme,o.netloc) for o in expected_origins}:
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

def limited(req,identity):
    host=(req.client.host if req.client else "unknown")[:100]
    ip=digest(host+":"+str(identity).strip().lower())
    now=int(time.time())
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
    u=user(req,True)
    if u:
        destination={"admin":"/manage","leader":"/teacher","student":"/study"}.get(u["role"],"/study")
        return RedirectResponse(destination,status_code=303)
    return HTMLResponse((ROOT/"web"/"login.html").read_text("utf8"))

@app.get("/study")
def study(req:Request):
    user(req)
    return HTMLResponse((ROOT/"web"/"study.html").read_text("utf8"))

def role_access_page(current_role,expected_role):
    role_name={"student":"学员","leader":"组长","admin":"管理员"}.get(current_role,"其他账号")
    home="/teacher" if current_role=="leader" else "/study"
    # All interpolated values above are from fixed, validated role labels and routes.
    return HTMLResponse(f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ACEpresso｜账户权限</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f4f2ed;color:#252622;font:16px/1.65 system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif}}
main{{max-width:620px;margin:12vh auto;padding:40px 42px;background:#fff;border:1px solid #d9d6ce}}
small{{color:#76746d;letter-spacing:.08em}}h1{{font-size:30px;line-height:1.25;margin:22px 0}}
p{{color:#52534c}}.status{{border-top:1px solid #ddd9d1;border-bottom:1px solid #ddd9d1;padding:17px 0;margin:28px 0}}
button,a.action{{display:inline-block;background:#303c35;color:#fff;padding:12px 20px;border:0;border-radius:3px;font:inherit;text-decoration:none;cursor:pointer}}
a.secondary{{color:#3d5043;margin-left:16px;text-decoration:underline}}#feedback{{color:#9e332d;font-size:14px}}
@media(max-width:650px){{main{{margin:20px 12px;padding:28px 22px}}h1{{font-size:26px}}}}
</style></head><body><main><small>3HFIT / ACEPRESSO</small>
<h1>当前账号没有此页面的访问权限</h1>
<div class="status">当前登录身份：<strong>{role_name}</strong><br>此页面需要：<strong>{expected_role}</strong></div>
<p>如果你需要进入管理员工作台，请退出当前账号，再使用管理员账号登录。不会删除此账号的学习记录。</p>
<button id="switch" type="button">退出当前账号并切换</button>
<a class="secondary" href="{home}">返回我的页面</a>
<p id="feedback" role="status"></p>
</main><script>
document.getElementById('switch').addEventListener('click',async function(){{
 const btn=this;btn.disabled=true;
 try{{
  const res=await fetch('/api/logout',{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json'}},body:'{{}}'}});
  if(!res.ok)throw Error('退出失败，请重试');
  location.replace('/');
 }}catch(err){{document.getElementById('feedback').textContent=err.message;btn.disabled=false}}
}});
</script></body></html>""",status_code=403)

@app.get("/manage")
def manage(req:Request):
    u=user(req,True)
    if not u:return RedirectResponse("/",status_code=303)
    if u["role"]!="admin":return role_access_page(u["role"],"管理员")
    return HTMLResponse((ROOT/"web"/"manage.html").read_text("utf8"))

@app.get("/teacher")
def teacher(req:Request):
    u=user(req,True)
    if not u:return RedirectResponse("/",status_code=303)
    if u["role"] not in ("leader","admin"):return role_access_page(u["role"],"组长或管理员")
    return HTMLResponse((ROOT/"web"/"teacher.html").read_text("utf8"))

@app.get("/api/health")
def health():return {"status":"ok"}

@app.get("/api/me")
def me(req:Request):return who(user(req))

@app.get("/recover-admin")
def admin_recovery_page():
    return HTMLResponse((ROOT/"web"/"recover.html").read_text("utf8"))

@app.post("/api/recover-admin")
async def admin_recover(req:Request):
    d=await payload(req,3000)
    limited(req,"admin-recovery")
    code=str(d.get("code","")).strip()
    password=str(d.get("password",""))
    confirm=str(d.get("confirm",""))
    if not 12<=len(password)<=128:
        error(400,"新密码长度必须为12至128个字符")
    if password!=confirm:
        error(400,"两次输入的新密码不一致")
    token_hash=os.getenv("ACE_ADMIN_RECOVERY_HASH","").strip().lower()
    try:
        expires_at=int(os.getenv("ACE_ADMIN_RECOVERY_EXPIRES","0"))
    except ValueError:
        expires_at=0
    now=int(time.time())
    if not token_hash or now>=expires_at or not hmac.compare_digest(digest(code),token_hash):
        error(400,"恢复码无效或已经过期")
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        c.execute("""CREATE TABLE IF NOT EXISTS admin_recovery_used
                  (token_hash TEXT PRIMARY KEY, used_at INTEGER NOT NULL)""")
        if c.execute("SELECT token_hash FROM admin_recovery_used WHERE token_hash=?",(token_hash,)).fetchone():
            error(400,"恢复码已经使用")
        admin=c.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        if not admin:
            error(404,"管理员账号不存在")
        c.execute("UPDATE users SET passhash=? WHERE id=?",(password_hash(password),admin["id"]))
        c.execute("DELETE FROM sessions WHERE user_id=?",(admin["id"],))
        c.execute("INSERT INTO admin_recovery_used(token_hash,used_at) VALUES(?,?)",(token_hash,now))
        c.execute("COMMIT")
    return {"ok":True}

@app.post("/api/register")
async def register(req:Request):
    d=await payload(req,5000);limited(req,d.get("login",""))
    login=str(d.get("login","")).strip().lower()
    name=str(d.get("name","")).strip()
    pw=str(d.get("password",""))
    invite=re.sub(r"[\s\u200b\ufeff]+","",str(d.get("invite",""))).upper()
    if not re.fullmatch(r"[\w.@-]{2,50}",login,flags=re.UNICODE):
        error(400,"登录账号需2—50个字符，可使用中文、英文、数字、点、下划线和短横线，不要包含空格")
    if not 1<=len(name)<=50:
        error(400,"请填写姓名或学习昵称，最多50个字符")
    if not 10<=len(pw)<=128:
        error(400,"注册密码须为10—128个字符")
    if not 10<=len(invite)<=70:
        error(400,"请粘贴完整的邀请码（以 ACE- 开头），不要填在登录账号栏")
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
    d=await payload(req,4000);limited(req,d.get("login",""))
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
    if not pw:error(400,"请输入当前密码")
    if len(new)<12:error(400,"新密码至少需要12个字符")
    if len(new)>128:error(400,"新密码不能超过128个字符")
    if not password_valid(pw,u["passhash"]):
        error(400,"当前密码不正确，请输入登录时使用的密码")
    if hmac.compare_digest(pw,new):error(400,"新密码不能与当前密码相同")
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

@app.get("/api/admin/leaders")
def admin_leader_list(req:Request):
    u=user(req)
    if u["role"]!="admin":error(403,"仅管理员可查看组长账号")
    with db() as c:
        rows=c.execute("""SELECT u.id,u.name,u.login,u.created_at,
            g.title AS group_title,co.title AS cohort
            FROM users u
            LEFT JOIN groups g ON u.group_id=g.id
            LEFT JOIN cohorts co ON g.cohort_id=co.id
            WHERE u.role='leader' ORDER BY u.id""").fetchall()
    return {"leaders":[dict(row) for row in rows]}

@app.post("/api/admin/leader-reset")
async def admin_issue_leader_reset(req:Request):
    u=user(req)
    if u["role"]!="admin":error(403,"仅管理员可以生成密码恢复码")
    d=await payload(req,1500)
    try: leader_id=int(d.get("leader_id",0))
    except (TypeError,ValueError):error(400,"请选择已注册的组长")
    if leader_id<1:error(400,"请选择已注册的组长")
    code="ACE-RST-"+secrets.token_hex(20).upper()
    hashed=digest(code)
    now=int(time.time())
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        leader=c.execute("SELECT id,login,role FROM users WHERE id=? AND role='leader'",(leader_id,)).fetchone()
        if not leader:error(404,"没有找到这个已注册组长账号")
        c.execute("UPDATE leader_password_resets SET used_at=? WHERE user_id=? AND used_at IS NULL",(now,leader_id))
        c.execute("""INSERT INTO leader_password_resets
                     (user_id,code_hash,issued_by,expires_at,created_at)
                     VALUES(?,?,?,?,?)""",
                  (leader_id,hashed,u["id"],now+24*3600,now))
        c.execute("COMMIT")
    return {"code":code,"login":leader["login"],"expires_in_hours":24}

@app.get("/recover-leader")
def leader_recovery_page():
    return HTMLResponse((ROOT/"web"/"recover-leader.html").read_text("utf8"))

@app.post("/api/recover-leader")
async def recover_leader(req:Request):
    d=await payload(req,2500)
    login=str(d.get("login","")).strip().lower()
    code=str(d.get("code","")).strip().upper()
    password=str(d.get("password",""))
    confirm=str(d.get("confirm",""))
    limited(req,"leader-reset-"+login)
    if len(login)<2 or not code.startswith("ACE-RST-") or len(code)>100:
        error(400,"账号或恢复码不正确，请核对管理员发送的信息")
    if not 10<=len(password)<=128:
        error(400,"新密码应为10至128个字符")
    if password!=confirm:
        error(400,"两次输入的新密码不一致")
    hashval=digest(code)
    now=int(time.time())
    newhash=password_hash(password)
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        target=c.execute("SELECT id FROM users WHERE login=? AND role='leader'",(login,)).fetchone()
        record=None
        if target:
            record=c.execute("""SELECT id FROM leader_password_resets
              WHERE user_id=? AND code_hash=? AND used_at IS NULL AND expires_at>?
              ORDER BY created_at DESC LIMIT 1""",
              (target["id"],hashval,now)).fetchone()
        if not target or not record:
            error(400,"账号或恢复码不正确，或恢复码已使用、已过期")
        c.execute("UPDATE users SET passhash=? WHERE id=?",(newhash,target["id"]))
        c.execute("DELETE FROM sessions WHERE user_id=?",(target["id"],))
        c.execute("UPDATE leader_password_resets SET used_at=? WHERE id=?",(now,record["id"]))
        c.execute("COMMIT")
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

@app.get("/api/leader/my-group")
def leader_group(req:Request):
    u=user(req)
    if u["role"]!="leader":
        error(403,"只有组长可管理学习小组")
    with db() as c:
        row=c.execute("""SELECT g.id,g.title,co.title AS cohort FROM groups g
                         JOIN cohorts co ON co.id=g.cohort_id WHERE g.id=?""",
                      (u["group_id"],)).fetchone()
        if not row:error(404,"小组不存在")
        students=c.execute("SELECT COUNT(*) AS n FROM users WHERE role='student' AND group_id=?",
                           (u["group_id"],)).fetchone()["n"]
        names=c.execute("SELECT name FROM users WHERE role='student' AND group_id=? ORDER BY id",
                        (u["group_id"],)).fetchall()
    return {"group_id":row["id"],"title":row["title"],"cohort":row["cohort"],
            "student_count":students,"students":[r["name"] for r in names]}

@app.post("/api/leader/my-group")
async def leader_name_group(req:Request):
    u=user(req)
    if u["role"]!="leader":error(403,"只有组长可管理学习小组")
    d=await payload(req,2500)
    title=str(d.get("title","")).strip()
    if not 2<=len(title)<=32:error(400,"小组名称需要2—32个字符")
    with db() as c:
        try:
            c.execute("UPDATE groups SET title=? WHERE id=?",(title,u["group_id"]))
        except sqlite3.IntegrityError:
            error(409,"该班期已存在同名小组，请换一个名称")
    return {"ok":True,"title":title,"group_id":u["group_id"]}

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
