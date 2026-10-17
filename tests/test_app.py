import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    return app.test_client()


def test_health(client):
    assert client.get("/health").json == {"status": "ok"}


def test_dashboard_needs_login(client):
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_register_login_add(client):
    client.post("/register", data={"email": "a@b.com", "password": "secret123"})
    r = client.post("/login", data={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 302
    client.post("/add", data={"company": "TCS", "role": "Developer", "status": "Applied"})
    assert b"TCS" in client.get("/").data


def test_wrong_password(client):
    client.post("/register", data={"email": "a@b.com", "password": "secret123"})
    r = client.post("/login", data={"email": "a@b.com", "password": "nope"})
    assert b"Wrong email or password" in r.data
