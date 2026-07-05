"""
BE-6: Auth flow depth tests.

Covers, with real assertions against the live FastAPI app + PostgreSQL:
    * register -> verify -> login (happy path)
    * MFA enable (setup/initiate + setup/verify with a real pyotp code) and
      login via /auth/login/mfa
    * failed-login lockout: 5 wrong passwords lock the account, with no 500s
      anywhere in the sequence
    * httpOnly refresh cookie is set on login, and /auth/refresh honors the
      cookie alone (no refresh_token in the request body)
"""
import pyotp

from tests.conftest import (
    API,
    DEFAULT_PASSWORD,
    unique_email,
    register_user,
    verify_user,
    login_user,
    register_verify_login,
    auth_headers,
)


class TestRegisterVerifyLogin:
    def test_register_returns_201_pending(self, client):
        email = unique_email("reg")
        r = register_user(client, email)
        assert r.status_code == 201
        body = r.json()
        assert body["email"] == email
        assert body["status"] == "PENDING" or str(body["status"]).endswith("PENDING")
        assert "user_id" in body

    def test_login_before_verification_is_rejected(self, client):
        email = unique_email("unverified")
        r = register_user(client, email)
        assert r.status_code == 201

        r_login = login_user(client, email)
        # Account is PENDING, not ACTIVE -> authenticate_user raises "not active"
        assert r_login.status_code == 401

    def test_duplicate_registration_rejected(self, client):
        email = unique_email("dup")
        r1 = register_user(client, email)
        assert r1.status_code == 201
        r2 = register_user(client, email)
        assert r2.status_code == 400

    def test_verify_activates_and_login_succeeds(self, client):
        email = unique_email("full")
        r = register_user(client, email)
        assert r.status_code == 201

        rv = verify_user(client, email)
        assert rv.status_code == 200
        assert rv.json()["email"] == email

        rl = login_user(client, email)
        assert rl.status_code == 200
        body = rl.json()
        assert "access_token" in body and body["access_token"]
        assert "refresh_token" in body and body["refresh_token"]
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == email
        assert body["requires_mfa"] is False

    def test_wrong_password_returns_401_not_500(self, client):
        email, _, _ = register_verify_login(client)
        r = login_user(client, email, password="TotallyWrongPass1!")
        assert r.status_code == 401


class TestFailedLoginLockout:
    def test_five_failures_lock_account_no_500(self, client):
        email, _, _ = register_verify_login(client)

        codes = []
        for _ in range(5):
            r = login_user(client, email, password="WrongPass999!")
            codes.append(r.status_code)

        # None of the 5 attempts should ever 500 (lockout bookkeeping must not
        # crash even as failed_login_attempts crosses the lockout threshold).
        assert all(c == 401 for c in codes), f"expected all 401, got {codes}"

        # 6th attempt (even with the correct password) must now be rejected
        # because the account is locked, and still must not 500.
        r6 = login_user(client, email, password=DEFAULT_PASSWORD)
        assert r6.status_code == 401
        assert "lock" in r6.text.lower()

    def test_locked_account_correct_password_still_locked(self, client):
        email, _, _ = register_verify_login(client)
        for _ in range(5):
            login_user(client, email, password="WrongPass999!")

        # Even the ORIGINAL correct password must not bypass the lock.
        r = login_user(client, email, password=DEFAULT_PASSWORD)
        assert r.status_code == 401
        assert "lock" in r.text.lower()


class TestMFA:
    def test_mfa_enable_and_login_flow(self, client, db_session):
        from app.models.user import User

        email, access_token, _ = register_verify_login(client)

        # Initiate MFA setup (generates + stores a secret, not yet enabled).
        r_init = client.post(f"{API}/auth/mfa/setup/initiate", headers=auth_headers(access_token))
        assert r_init.status_code == 200
        assert "qr_code_url" in r_init.json()

        # Read the (temporary) secret directly from the DB, exactly as the
        # verification harness does, to compute a valid TOTP code.
        user_row = db_session.query(User).filter(User.email == email).first()
        assert user_row is not None
        secret = user_row.mfa_secret
        assert secret, "mfa_secret must be populated after setup/initiate"

        code = pyotp.TOTP(secret).now()
        r_verify = client.post(
            f"{API}/auth/mfa/setup/verify",
            headers=auth_headers(access_token),
            json={"mfa_code": code},
        )
        assert r_verify.status_code == 200
        body = r_verify.json()
        assert "backup_codes" in body and len(body["backup_codes"]) == 10

        # Plain /auth/login must now require MFA (not immediately succeed).
        r_plain_login = login_user(client, email)
        assert r_plain_login.status_code == 401
        assert "mfa" in r_plain_login.text.lower()

        # /auth/login/mfa with a fresh valid TOTP code succeeds.
        code2 = pyotp.TOTP(secret).now()
        r_mfa_login = client.post(
            f"{API}/auth/login/mfa",
            json={"email": email, "password": DEFAULT_PASSWORD, "mfa_code": code2},
        )
        assert r_mfa_login.status_code == 200
        mfa_body = r_mfa_login.json()
        assert "access_token" in mfa_body and mfa_body["access_token"]
        assert mfa_body["user"]["email"] == email

    def test_mfa_login_with_wrong_code_rejected(self, client, db_session):
        from app.models.user import User

        email, access_token, _ = register_verify_login(client)
        client.post(f"{API}/auth/mfa/setup/initiate", headers=auth_headers(access_token))
        user_row = db_session.query(User).filter(User.email == email).first()
        secret = user_row.mfa_secret
        code = pyotp.TOTP(secret).now()
        client.post(
            f"{API}/auth/mfa/setup/verify",
            headers=auth_headers(access_token),
            json={"mfa_code": code},
        )

        r_bad = client.post(
            f"{API}/auth/login/mfa",
            json={"email": email, "password": DEFAULT_PASSWORD, "mfa_code": "000000"},
        )
        assert r_bad.status_code == 401


class TestRefreshCookie:
    def test_login_sets_httponly_refresh_cookie(self, client):
        email, _, login_response = register_verify_login(client)

        set_cookie_header = login_response.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie_header
        assert "httponly" in set_cookie_header.lower()

        # TestClient's cookie jar should also have picked it up.
        assert client.cookies.get("refresh_token") is not None

    def test_refresh_via_cookie_only_no_body_token(self, client):
        """
        /auth/refresh must accept the refresh token from the httpOnly cookie
        alone -- i.e. it must succeed even when the JSON body omits
        `refresh_token` entirely (the primary point of having the cookie).

        The login cookie is set with Secure=True (correct: it must never be
        sent over plain HTTP in production). httpx/TestClient correctly
        enforces RFC 6265 and will NOT auto-replay a Secure cookie against the
        plain-http `testserver` origin -- the cookie does land in
        `client.cookies` (proven by the sibling
        test_login_sets_httponly_refresh_cookie test) but isn't attached to
        outgoing requests on its own. That's httpx behaving correctly, not an
        app bug. To exercise the server's "read refresh token from cookie"
        code path, attach the cookie explicitly on this one call, exactly as
        a real browser would when the scheme really is HTTPS.
        """
        email, access_token, login_response = register_verify_login(client)

        refresh_cookie_value = client.cookies.get("refresh_token")
        assert refresh_cookie_value is not None

        r = client.post(
            f"{API}/auth/refresh",
            json={},
            cookies={"refresh_token": refresh_cookie_value},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "access_token" in body and body["access_token"]
        assert body["user"]["email"] == email

    def test_refresh_without_cookie_or_body_rejected(self, client):
        """A bare /auth/refresh call with neither cookie nor body token, and
        no Authorization header, must be rejected (401) rather than crash."""
        # Use a client with no cookies and no auth header to guarantee no
        # refresh token is available via any channel.
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app

        with TestClient(fastapi_app, raise_server_exceptions=False) as bare_client:
            r = bare_client.post(f"{API}/auth/refresh", json={})
            assert r.status_code == 401
