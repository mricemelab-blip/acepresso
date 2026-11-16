import os
import sys
import tempfile
from pathlib import Path

db_file = Path(tempfile.mkdtemp()) / "acepresso-recovery-test.sqlite3"
os.environ["ACE_DB_PATH"] = str(db_file)
os.environ["ACE_HTTPS"] = "0"
os.environ["ACE_ADMIN_LOGIN"] = "test-admin"
os.environ["ACE_ADMIN_PASSWORD"] = "test-admin-password-123456"
for k in ("ACE_ENROLL_BATCH", "ACE_ENROLL_SEED", "ACE_ENROLL_ADMIN_VERIFIER"):
    os.environ.pop(k, None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from server.app import app, db, password_hash


def test_student_recovery_preserves_existing_data():
    with db() as c:
        c.execute("INSERT INTO groups(cohort_id,title) VALUES(1,'D组')")
        group_id = c.execute("SELECT id FROM groups WHERE title='D组'").fetchone()["id"]
        user_id = c.execute(
            "INSERT INTO users(name,login,passhash,role,group_id,created_at) VALUES(?,?,?,?,?,?)",
            ("曾思佳", "zeng-test", password_hash("original-password-1234"), "student", group_id, 1)
        ).lastrowid
        c.execute("INSERT INTO progress(user_id,data,updated_at) VALUES(?,?,?)",
                  (user_id, '{"submitted":{"1":true},"notes":{"1":"existing"}}', 123))
    stranger = TestClient(app)
    assert stranger.get("/api/admin/students", params={"q": "曾思佳"}).status_code == 401
    assert stranger.post("/api/admin/student-reset", json={"student_id": user_id}).status_code == 401

    admin = TestClient(app)
    r = admin.post("/api/login", json={"login": "test-admin", "password": "test-admin-password-123456"})
    assert r.status_code == 200, r.text
    search = admin.get("/api/admin/students", params={"q": "曾思", "group_id": group_id})
    assert search.status_code == 200, search.text
    students = search.json()["students"]
    assert len(students) == 1
    assert students[0]["name"] == "曾思佳"
    assert students[0]["login"] == "zeng-test"
    assert students[0]["has_progress"] == 1
    assert "passhash" not in students[0]
    assert admin.get("/api/admin/students", params={"group_id": group_id}).status_code == 200
    assert admin.get("/api/admin/students").status_code == 400

    issued = admin.post("/api/admin/student-reset", json={"student_id": user_id})
    assert issued.status_code == 200, issued.text
    first = issued.json()["code"]
    assert first.startswith("ACE-SRST-") and len(first) == 49
    next_issued = admin.post("/api/admin/student-reset", json={"student_id": user_id})
    assert next_issued.status_code == 200
    second = next_issued.json()["code"]
    assert first != second
    assert stranger.get("/recover-student").status_code == 200
    obsolete = stranger.post("/api/recover-student", json={
        "login": "zeng-test", "code": first, "password": "new-password-very-secure-123", "confirm": "new-password-very-secure-123"})
    assert obsolete.status_code == 400
    recovered = stranger.post("/api/recover-student", json={
        "login": "zeng-test", "code": second, "password": "new-password-very-secure-123", "confirm": "new-password-very-secure-123"})
    assert recovered.status_code == 200, recovered.text
    repeat = stranger.post("/api/recover-student", json={
        "login": "zeng-test", "code": second, "password": "another-password-very-secure", "confirm": "another-password-very-secure"})
    assert repeat.status_code == 400

    old = stranger.post("/api/login", json={"login": "zeng-test", "password": "original-password-1234"})
    assert old.status_code == 401
    new = stranger.post("/api/login", json={"login": "zeng-test", "password": "new-password-very-secure-123"})
    assert new.status_code == 200
    with db() as c:
        user = c.execute("SELECT id,name,login,role,group_id FROM users WHERE id=?", (user_id,)).fetchone()
        progress = c.execute("SELECT data,updated_at FROM progress WHERE user_id=?", (user_id,)).fetchone()
        assert dict(user) == {"id":user_id, "name":"曾思佳", "login":"zeng-test",
                              "role":"student", "group_id":group_id}
        assert progress["updated_at"] == 123
        assert '"existing"' in progress["data"]
