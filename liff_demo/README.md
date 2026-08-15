# Django + LINE LIFF Login Example

A minimal, working example of "Login with LINE" inside a LIFF app, wired into
Django's normal session/auth system.

## How it works

1. **`templates/accounts/liff_login.html`** loads the LIFF SDK and calls
   `liff.init({liffId})`. If the user isn't logged in to LINE yet, it shows a
   button that calls `liff.login()`. Once logged in, the page reads
   `liff.getIDToken()` — a JWT LINE issues that proves who the user is — and
   POSTs it to the backend.
2. **`accounts/views.py: liff_verify`** takes that token and calls LINE's own
   `https://api.line.me/oauth2/v2.1/verify` endpoint server-to-server. This is
   the important security step: never trust a token just because the browser
   sent it — always verify it directly with LINE, and check the `aud` claim
   matches your Channel ID.
3. Once verified, the view gets-or-creates a `LineProfile` (and its linked
   Django `User`), then calls `django.contrib.auth.login()` — from that point
   on it's a completely normal Django session, so `@login_required`,
   `request.user`, etc. all work as usual.
4. **`accounts/views.py: profile`** is a normal `@login_required` view showing
   the signed-in user's LINE display name and avatar.

## One-time setup in the LINE Developers Console

1. Go to https://developers.line.biz/console/ and create a provider (if you
   don't have one) and a **LINE Login** channel inside it.
2. Open that channel → **LIFF** tab → **Add** a LIFF app.
   - Endpoint URL: your login page's public HTTPS URL
     (e.g. `https://yourdomain.com/accounts/`). LIFF requires HTTPS, so for
     local dev use `ngrok`/`cloudflared` to tunnel `runserver`.
   - Scope: enable **openid** (required for `getIDToken()`) and **profile**.
   - Copy the generated **LIFF ID**.
3. On the channel's **Basic settings** tab, copy the **Channel ID** — this is
   the value the backend checks against the token's `aud` claim.
4. Set both as environment variables before running the server:

   ```bash
   export LIFF_ID="1234567890-AbCdEfGh"
   export LINE_CHANNEL_ID="1234567890"
   ```

## Run it

```bash
pip install django requests
python manage.py migrate
python manage.py runserver
```

Because LIFF apps must be opened through `https://liff.line.me/{liffId}` (or
inside the LINE app itself) for the SDK to fully initialize, use a tunnel
(ngrok, Cloudflare Tunnel, etc.) pointed at `runserver` during local testing,
and set that tunnel's HTTPS URL as the LIFF endpoint URL in step 2 above.

## Files

- `accounts/models.py` — `LineProfile` (one-to-one with Django's `User`, stores `line_user_id`, name, avatar)
- `accounts/views.py` — `liff_login_page`, `liff_verify` (the token-verification API), `profile`, `liff_logout`
- `accounts/urls.py` — routes under `/accounts/`
- `templates/accounts/liff_login.html` — LIFF SDK bootstrap + login button
- `templates/accounts/profile.html` — post-login page
