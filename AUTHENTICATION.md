# TEE Authentication Foundation

## Local configuration

1. Copy `.env.example` to `.env` in the backend repository root.
2. Set the real `DATABASE_URL` and SMTP credentials.
3. Generate a new JWT signing key and put it in `.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set the output as `JWT_SECRET_KEY`. Use a fresh key: the previous signing key was hardcoded in source and must be treated as exposed.

4. Install dependencies and start the backend:

```powershell
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The application creates the `auth_challenges` table on startup. The database must already contain the existing `users` table.

## Login flow

1. `POST /api/auth/login` accepts a user's name or email and password.
2. Passwords are verified with Argon2id. Existing plaintext or legacy PBKDF2 passwords are upgraded to Argon2id after a successful login.
3. A six-digit email OTP is stored as a keyed digest in `auth_challenges` and expires after five minutes.
4. `POST /api/auth/verify-2fa` verifies the OTP and returns a 60-minute JWT.
5. Protected application endpoints require `Authorization: Bearer <access_token>`.
6. `GET /api/auth/me` returns the authenticated user and is used by the frontend to validate a stored session.

SMS verification is intentionally disabled until a real SMS provider is configured and tested.

## Password reset

- `POST /api/auth/forgot-password` sends a reset OTP without disclosing whether the email belongs to an account.
- `POST /api/auth/verify-reset-otp` validates the OTP and issues a short-lived one-time reset token.
- `POST /api/auth/reset-password` consumes that token and stores a new Argon2id password hash.

## Security notes

- OTP challenges and reset tokens are stored in the database, not process memory.
- OTPs expire after five minutes, allow at most five attempts, and resend requests have a cooldown.
- Keep `.env` out of Git. Rotate JWT keys if they are exposed.
- Deploy behind HTTPS and configure rate limiting at the reverse proxy/API gateway, especially for login and password-reset endpoints.
- The frontend currently keeps the access token in localStorage; a production deployment should consider migrating to Secure, HttpOnly, SameSite cookies to reduce token exposure from XSS.
- A 60-minute access token has no refresh-token flow yet; users sign in again after expiry.
