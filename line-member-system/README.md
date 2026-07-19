# LINE OA Member Registration System

Django + PostgreSQL backend, static LIFF frontend (vanilla HTML/CSS/JS).

```
line-member-system/
├── backend/                 Django project (API)
│   ├── config/               settings, urls, wsgi
│   ├── members/               model, serializers, views, LINE client
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/                 LIFF app (deployed to Vercel)
    ├── index.html
    ├── app.js
    ├── style.css
    └── vercel.json
```

## How auth works (read this first)

The frontend never sends a LINE user id directly — it sends the ID token
from `liff.getIDToken()` on every API call as `Authorization: Bearer <token>`.
The backend verifies that token with LINE's own `/oauth2/v2.1/verify`
endpoint before trusting *anything* about who's calling. This stops
someone from opening dev tools and registering a member record under a
LINE user id that isn't theirs.

---

## 1. LINE Developers Console setup

1. **Create a provider** (if you don't have one) at
   https://developers.line.biz/console/.
2. **Create a Messaging API channel** — this is your LINE Official
   Account. Note the **Channel access token** (Messaging API tab →
   issue a long-lived token) — this goes in `LINE_CHANNEL_ACCESS_TOKEN`.
3. **Create a LINE Login channel** in the same provider.
   - Under the Login channel's **LIFF** tab, click **Add**.
   - **Size**: `Full` (recommended for a form).
   - **Endpoint URL**: your Vercel URL, e.g. `https://your-liff-app.vercel.app`
     (you'll get this in step 3 below — you can update it after deploying).
   - **Scope**: check `profile` and `openid` (openid is required to get an ID token).
   - **Bot link feature**: `On (Aggressive)` and link it to the Messaging
     API channel from step 2 — this is what lets a LIFF app opened from
     the OA's rich menu also receive push messages from that OA.
   - Save, then copy the **LIFF ID** (format `1234567890-abcdefgh`).
4. On the Login channel's **Basic settings** tab, copy the **Channel ID**
   — this is `LINE_LOGIN_CHANNEL_ID` (used server-side to validate the
   token's `aud` claim).
5. **Set up the Rich Menu** on the Messaging API channel (Console →
   Messaging API → Rich menus, or via the Messaging API):
   - Add an action of type **LIFF** pointing at
     `https://liff.line.me/<your-LIFF-ID>`.
   - Set it as the default rich menu for the OA.

---

## 2. Backend: local setup & configuration

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

| Variable | Where to get it |
|---|---|
| `DJANGO_SECRET_KEY` | any long random string (`python -c "import secrets;print(secrets.token_urlsafe(50))"`) |
| `DJANGO_ALLOWED_HOSTS` | your API's domain once deployed |
| `DATABASE_URL` | your Postgres connection string |
| `CORS_ALLOWED_ORIGINS` | your Vercel frontend URL, exact origin, no trailing slash |
| `LINE_LOGIN_CHANNEL_ID` | step 4 above |
| `LINE_CHANNEL_ACCESS_TOKEN` | step 2 above |
| `LIFF_ID` | step 3 above |

Create the Postgres database, then run migrations:

```bash
createdb line_members   # or use your DB host's dashboard
python manage.py migrate
python manage.py createsuperuser   # to view members at /admin/
python manage.py runserver
```

API is now at `http://127.0.0.1:8000/api/members/`.

**Endpoints:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/members/status/` | Is this LINE user already registered? |
| POST | `/api/members/register/` | Create/update the member record + push Flex card |
| GET | `/api/members/card/` | Re-fetch the current user's card |

All three require `Authorization: Bearer <LIFF ID token>`.

---

## 3. Frontend: local setup & deployment (Vercel)

Edit the two values at the top of `frontend/app.js`:

```js
const CONFIG = {
  LIFF_ID: "1234567890-abcdefgh",              // from step 1.3
  API_BASE_URL: "https://your-api-domain.com/api/members",
};
```

Deploy:

```bash
cd frontend
npm i -g vercel   # if you don't have it
vercel --prod
```

Vercel will give you a URL like `https://line-member-system.vercel.app`.
Go back to the LIFF app in the Developers Console and set that as the
**Endpoint URL** (step 1.3). Also add it to `CORS_ALLOWED_ORIGINS` in the
backend's `.env` and redeploy the backend.

> LIFF apps must be served over HTTPS — Vercel gives you this by default,
> so no extra TLS setup is needed here.

---

## 4. Backend deployment (Render / Railway — either works)

Both platforms auto-detect Django. General steps (shown for Render):

1. Push `backend/` to a Git repo.
2. In Render: **New → Web Service**, point at the repo, root directory
   `backend/`.
3. **Build command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
4. **Start command**: `gunicorn config.wsgi`
5. Add a **PostgreSQL** instance (Render → New → PostgreSQL) and copy its
   internal connection string into `DATABASE_URL`.
6. Add all the other env vars from `.env` in the service's Environment tab.
7. Deploy. Your API is now at `https://<service>.onrender.com`.

Update `frontend/app.js`'s `API_BASE_URL` to that URL and redeploy the
frontend (`vercel --prod`).

---

## 5. End-to-end test

1. Open the OA in LINE, tap the rich menu button.
2. The LIFF app opens, calls `liff.getProfile()`, and shows the
   registration form pre-filled with your LINE display name/photo.
3. Fill in phone, email, name, date of birth → **Create my card**.
4. You should land on the member card screen, and a matching Flex
   Message card should appear in your chat with the OA.
5. Reopen the rich menu button again — you should go straight to the
   member card screen this time (no form), because `/status/` now
   reports `registered: true`.

## Notes on the "Django 6.x" requirement

Django 6.0 hadn't been released as of this build, so the project targets
the current stable series (5.1). Everything here — settings module
layout, `STORAGES` config, DRF integration — is forward-compatible; bump
the `Django` pin in `requirements.txt` when 6.x ships.
