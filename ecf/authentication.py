from django.core.signing import BadSignature, SignatureExpired, loads
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from administration.models import User


class ECFPrincipal:
    """Small authenticated principal for the legacy application user model."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, user: User):
        self.id = user.id
        self.company_id = user.company_id
        self.email = user.email
        self.role = user.userRole


class ECFUserAuthentication(BaseAuthentication):
    """Authenticate e-CF API requests with the signed token issued at login."""

    max_age_seconds = 8 * 60 * 60

    def authenticate(self, request):
        token = request.headers.get("X-Auth-Token")
        if not token:
            return None

        try:
            payload = loads(token, salt="ecf-api", max_age=self.max_age_seconds)
        except SignatureExpired as exc:
            raise AuthenticationFailed("La sesión expiró; inicia sesión nuevamente.") from exc
        except BadSignature as exc:
            raise AuthenticationFailed("Token de sesión inválido.") from exc

        if not isinstance(payload, dict):
            raise AuthenticationFailed("Token de sesión inválido.")

        user = User.objects.filter(
            pk=payload.get("user_id"),
            company_id=payload.get("company_id"),
        ).first()
        if user is None:
            raise AuthenticationFailed("La cuenta ya no está disponible.")

        return ECFPrincipal(user), token
