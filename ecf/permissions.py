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
        if getattr(view, "action", "") in {"customer_fiscal_id", "checkout_sale", "reserve_encf", "build_xml", "sign", "build_rfce", "sign_rfce", "send_rfce", "send", "query_result", "build_representation", "update_draft"}:
            return bool(request.user and request.user.is_authenticated and getattr(request.user, "role", None) in {"Admin", "Owner", "Caja"})
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if request.method == "POST" and getattr(request.user, "role", None) == "Caja":
            return obj.environment == "prod" and obj.document_type in {"31", "32"} and bool(obj.invoice_id)
        return True
