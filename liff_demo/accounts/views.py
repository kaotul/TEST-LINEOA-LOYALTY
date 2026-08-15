import json

import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import LineProfile

User = get_user_model()

LINE_VERIFY_URL = 'https://api.line.me/oauth2/v2.1/verify'


def liff_login_page(request):
    """
    Renders the page that boots the LIFF SDK.
    The page itself decides (in JS) whether to show a "Login with LINE"
    button or auto-redirect, depending on liff.isLoggedIn().
    """
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    return render(request, 'accounts/liff_login.html', {'liff_id': settings.LIFF_ID})


@csrf_exempt  # the request comes from JS running inside the LIFF browser; verify via LINE's endpoint instead
@require_POST
def liff_verify(request):
    """
    Body: {"id_token": "<the JWT from liff.getIDToken()>"}

    Verifies the token directly with LINE's servers (never trust a token
    just because the browser sent it), then creates/updates a local user
    and starts a normal Django session.
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)

    id_token = payload.get('id_token')
    if not id_token:
        return JsonResponse({'ok': False, 'error': 'missing_id_token'}, status=400)

    # --- Step 1: verify the ID token with LINE (server-to-server) ---
    verify_resp = requests.post(
        LINE_VERIFY_URL,
        data={'id_token': id_token, 'client_id': settings.LINE_CHANNEL_ID},
        timeout=8,
    )
    if verify_resp.status_code != 200:
        return JsonResponse({'ok': False, 'error': 'token_verify_failed'}, status=401)

    claims = verify_resp.json()
    # claims typically contains: iss, sub, aud, exp, iat, name, picture, email (if scope granted)

    if claims.get('aud') != settings.LINE_CHANNEL_ID:
        # audience must match your channel, otherwise this token was issued for a different app
        return JsonResponse({'ok': False, 'error': 'audience_mismatch'}, status=401)

    line_user_id = claims['sub']
    display_name = claims.get('name', '')
    picture_url = claims.get('picture', '')
    email = claims.get('email', '')

    # --- Step 2: get or create the local Django user tied to this LINE id ---
    profile = LineProfile.objects.filter(line_user_id=line_user_id).first()
    if profile:
        user = profile.user
        profile.display_name = display_name
        profile.picture_url = picture_url
        profile.email = email
        profile.save(update_fields=['display_name', 'picture_url', 'email', 'updated_at'])
    else:
        # username must be unique; the LINE user id is a safe, stable choice
        user = User.objects.create_user(
            username=f'line_{line_user_id}',
            email=email,
        )
        user.first_name = display_name[:150]
        user.save(update_fields=['first_name'])
        profile = LineProfile.objects.create(
            user=user,
            line_user_id=line_user_id,
            display_name=display_name,
            picture_url=picture_url,
            email=email,
        )

    # --- Step 3: log the user into a normal Django session ---
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    auth_login(request, user)

    return JsonResponse({'ok': True, 'redirect_url': '/accounts/profile/'})


@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {
        'line_profile': getattr(request.user, 'line_profile', None),
    })


def liff_logout(request):
    auth_logout(request)
    return redirect('accounts:liff_login_page')
