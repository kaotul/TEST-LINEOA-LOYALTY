from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler as drf_exception_handler

from .line_client import LineTokenError, push_member_card, verify_id_token
from .models import Member
from .serializers import MemberCardSerializer, MemberRegistrationSerializer


def api_exception_handler(exc, context):
    """Wrap DRF's default handler so every error response has a stable {"detail": ...} shape."""
    response = drf_exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and "detail" not in response.data:
        # e.g. serializer field errors -> flatten into a single readable detail string
        response.data = {"detail": response.data}
    return response


def _verify_request(request) -> dict:
    """
    Pull the LIFF ID token out of the Authorization header and verify it
    with LINE. Raises LineTokenError on failure (caught by callers).

    Frontend sends: Authorization: Bearer <id_token from liff.getIDToken()>
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise LineTokenError("Missing Authorization header.")
    id_token = auth_header[len("Bearer "):].strip()
    return verify_id_token(id_token)


class MemberStatusView(APIView):
    """
    GET /api/members/status/
    Tells the LIFF app whether the current LINE user is already a member,
    so it can skip straight to the member card instead of showing the form.
    """

    def get(self, request):
        try:
            claims = _verify_request(request)
        except LineTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        member = Member.objects.filter(line_user_id=claims["sub"]).first()
        return Response(
            {
                "registered": member is not None,
                "member": MemberCardSerializer(member).data if member else None,
                "profile": {"display_name": claims.get("name"), "picture_url": claims.get("picture")},
            }
        )


class MemberRegisterView(APIView):
    """
    POST /api/members/register/
    Body: { first_name, last_name, phone_number, email, date_of_birth }
    Creates (or updates, if the user re-submits) the member record for the
    LINE user identified by the verified ID token, then pushes the Flex
    Message member card into the OA chat.
    """

    def post(self, request):
        try:
            claims = _verify_request(request)
        except LineTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = MemberRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member, _created = Member.objects.update_or_create(
            line_user_id=claims["sub"],
            defaults={
                "display_name": claims.get("name", ""),
                "picture_url": claims.get("picture", ""),
                **serializer.validated_data,
            },
        )

        # Best-effort; registration succeeds even if this fails (see line_client).
        push_member_card(claims["sub"], member)

        return Response(MemberCardSerializer(member).data, status=status.HTTP_201_CREATED)


class MemberCardView(APIView):
    """GET /api/members/card/ -- fetch the current user's member card again later."""

    def get(self, request):
        try:
            claims = _verify_request(request)
        except LineTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        member = Member.objects.filter(line_user_id=claims["sub"]).first()
        if member is None:
            return Response({"detail": "Not a member yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MemberCardSerializer(member).data)
