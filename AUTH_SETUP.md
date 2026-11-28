# TEE authentication delivery setup

The login flow supports email OTP and SMS OTP through the existing Text.lk service.

## Local development: print OTPs in the backend terminal

Add this setting to the backend `.env` file:

```env
OTP_DEBUG_LOG=true
```

Restart FastAPI. When a login or resend creates an OTP, the backend terminal prints a line beginning with `[TEE OTP DEBUG]`. If SMTP or Text.lk is not configured/reachable, the OTP remains usable for local testing and the terminal is used as the development delivery fallback.

**Never enable `OTP_DEBUG_LOG=true` in production.** It deliberately exposes authentication codes in server logs. Set it to `false` (or remove it) before deployment.

## Email delivery (SMTP)

Configure these values in the backend `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-sending-account@gmail.com
SMTP_PASSWORD=your-google-app-password
SMTP_FROM_EMAIL=your-sending-account@gmail.com
SMTP_FROM_NAME=TEE Estate System
OTP_DEBUG_LOG=true
```

For Gmail, use a Google App Password where the account supports it; do not use the normal account password. Port 587 uses STARTTLS. Port 465 uses implicit TLS. The sender address should be authorized by the SMTP provider.

If credentials are missing or SMTP rejects the connection, the API returns HTTP 503 when debug mode is disabled instead of silently reporting that an email was sent.

## SMS delivery (Text.lk)

The backend already contains a Text.lk HTTP SMS integration. Configure:

```env
TEXTLK_API_TOKEN=your-textlk-api-token
TEXTLK_SENDER_ID=your-approved-sender-id
```

The phone number must be a Sri Lankan mobile number. Supported formats include `0771234567`, `+94771234567`, and `94771234567`. Legacy worker records stored as a nine-digit numeric value beginning with 7 are normalized as well.

Text.lk account activation, API credits, and sender-ID approval are provider-side requirements. The application cannot send a real SMS until valid credentials and an approved sender ID are supplied.

## Behaviour

- Login defaults to email OTP.
- On the OTP screen, **Change verifying Method** can request a new code by SMS or email.
- Resend/change-method requests are throttled to one per 60 seconds.
- Codes expire after five minutes and are limited to five verification attempts.
- OTPs are printed only when `OTP_DEBUG_LOG=true`.
