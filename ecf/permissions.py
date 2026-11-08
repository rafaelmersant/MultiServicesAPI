from rest_framework.permissions import BasePermission


class ECFAdminOrOwnerPermission(BasePermission):
    """Only company administrators may configure or transmit e-CF documents."""

    message = "Solo Admin y Owner pueden administrar comprobantes e-CF."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in {"Admin", "Owner"}
        )


class ECFCompanyAccessPermission(ECFAdminOrOwnerPermission):
    def has_permission(self, request, view):
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return bool(request.user and request.user.is_authenticated)
        return super().has_permission(request, view)
