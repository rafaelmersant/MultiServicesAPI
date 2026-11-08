"""Protect fiscal source data once a production e-NCF has been reserved."""
from rest_framework.exceptions import ValidationError
from django.db import transaction


def lock_source(invoice_id):
    from sales.models import InvoicesHeader
    return InvoicesHeader.objects.select_for_update().filter(pk=invoice_id).first()


def is_electronic_sale(invoice_id):
    from .models import ElectronicInvoice
    return ElectronicInvoice.objects.filter(invoice_id=invoice_id, environment="prod").exclude(encf__isnull=True).exclude(encf="").exists()


def require_editable_sale(invoice_id):
    if is_electronic_sale(invoice_id):
        raise ValidationError("La venta tiene un e-NCF reservado. Conserva sus datos fiscales; corrige mediante el flujo e-CF correspondiente.")


class ElectronicHeaderProtection:
    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        lock_source(instance.pk)
        if is_electronic_sale(instance.pk):
            # Collection/printing flags remain operational. Fiscal data is immutable.
            protected = {"company_id", "customer_id", "paymentMethod", "ncf", "sequence", "subtotal", "itbis", "discount", "invoiceType", "invoiceStatus", "creationDate"}
            for field in protected.intersection(serializer.validated_data):
                if serializer.validated_data[field] != getattr(instance, field):
                    require_editable_sale(instance.pk)
        super().perform_update(serializer)

    @transaction.atomic
    def perform_destroy(self, instance):
        lock_source(instance.pk)
        require_editable_sale(instance.pk)
        super().perform_destroy(instance)


class ElectronicDetailProtection:
    @transaction.atomic
    def perform_create(self, serializer):
        lock_source(serializer.validated_data.get("invoice_id"))
        require_editable_sale(serializer.validated_data.get("invoice_id"))
        super().perform_create(serializer)

    @transaction.atomic
    def perform_update(self, serializer):
        ids = {serializer.instance.invoice_id, serializer.validated_data.get("invoice_id", serializer.instance.invoice_id)}
        for invoice_id in sorted(ids):
            lock_source(invoice_id)
        require_editable_sale(serializer.instance.invoice_id)
        if "invoice_id" in serializer.validated_data:
            require_editable_sale(serializer.validated_data["invoice_id"])
        super().perform_update(serializer)

    @transaction.atomic
    def perform_destroy(self, instance):
        lock_source(instance.invoice_id)
        require_editable_sale(instance.invoice_id)
        super().perform_destroy(instance)
