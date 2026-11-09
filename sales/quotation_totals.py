"""Quotation totals derived from saved lines, without inventory operations."""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import QuotationsHeader, QuotationsDetail


def quotation_totals(lines):
    subtotal = discount = tax = Decimal('0')
    for line in lines:
        quantity, price, line_discount, line_tax = (
            Decimal(line[name]) for name in ('quantity', 'price', 'discount', 'itbis')
        )
        gross = (quantity * price).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        if quantity <= 0 or price < 0 or line_discount < 0 or line_discount > gross or line_tax < 0:
            raise ValidationError('Cantidad, precio, descuento o ITBIS inválido en la cotización.')
        subtotal += gross
        discount += line_discount
        tax += (line_tax * (gross - line_discount) / gross if gross else Decimal('0')).quantize(
            Decimal('.001'), rounding=ROUND_HALF_UP
        )
    return dict(subtotal=subtotal, discount=discount, itbis=tax)


def sync_quotation_totals(header):
    totals = quotation_totals(QuotationsDetail.objects.filter(header_id=header.pk).values(
        'quantity', 'price', 'discount', 'itbis'
    ))
    for name, value in totals.items():
        setattr(header, name, value)
    header.save(update_fields=('subtotal', 'discount', 'itbis'))


class QuotationHeaderTotalsMixin:
    @transaction.atomic
    def perform_create(self, serializer):
        # A newly created quotation has no persisted lines yet.
        serializer.save(subtotal=0, discount=0, itbis=0)

    @transaction.atomic
    def perform_update(self, serializer):
        QuotationsHeader.objects.select_for_update().get(pk=serializer.instance.pk)
        header = serializer.save()
        sync_quotation_totals(header)


class QuotationDetailTotalsMixin:
    @transaction.atomic
    def perform_create(self, serializer):
        header = QuotationsHeader.objects.select_for_update().get(pk=serializer.validated_data['header_id'])
        serializer.save()
        sync_quotation_totals(header)

    @transaction.atomic
    def perform_update(self, serializer):
        header_id = serializer.instance.header_id
        if serializer.validated_data.get('header_id', header_id) != header_id:
            raise ValidationError('No se puede mover un detalle a otra cotización.')
        header = QuotationsHeader.objects.select_for_update().get(pk=header_id)
        serializer.save()
        sync_quotation_totals(header)

    @transaction.atomic
    def perform_destroy(self, instance):
        header = QuotationsHeader.objects.select_for_update().get(pk=instance.header_id)
        instance.delete()
        sync_quotation_totals(header)
