import os
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MultiServices.settings')
import django
django.setup()
from sales.quotation_totals import quotation_totals, sync_quotation_totals, QuotationDetailTotalsMixin
from rest_framework.exceptions import ValidationError

def line(**kw):
    return dict(quantity='2', price='118', discount='20', itbis='36', **kw) if not kw else {**line(), **kw}

def test_quotation_discount_and_zero_tax():
    assert quotation_totals([line(), line(quantity='1',price='100',discount='0',itbis='0')]) == dict(subtotal=Decimal('336'),discount=Decimal('20'),itbis=Decimal('32.949'))

def test_empty_quotation_totals_zero():
    assert quotation_totals([]) == dict(subtotal=0,discount=0,itbis=0)

@pytest.mark.parametrize('changes',[{'quantity':'0'},{'price':'-1'},{'discount':'-1'},{'discount':'237'},{'itbis':'-1'}])
def test_bad_lines_rejected(changes):
    with pytest.raises(ValidationError):
        quotation_totals([line(**changes)])

def test_sync_updates_only_header_totals():
    header=SimpleNamespace(pk=3, save=MagicMock())
    with patch('sales.quotation_totals.QuotationsDetail.objects.filter') as rows:
        rows.return_value.values.return_value=[line()]
        sync_quotation_totals(header)
    header.save.assert_called_once_with(update_fields=('subtotal','discount','itbis'))
    assert header.subtotal == 236

@pytest.mark.parametrize('operation', ['create','update','destroy'])
def test_each_line_operation_locks_parent_and_syncs_saved_lines(operation):
    instance=SimpleNamespace(header_id=3, delete=MagicMock())
    serializer=SimpleNamespace(validated_data={'header_id':3},instance=instance,save=MagicMock())
    with patch('sales.quotation_totals.QuotationsHeader.objects.select_for_update') as lock, patch('sales.quotation_totals.sync_quotation_totals') as sync:
        method=getattr(QuotationDetailTotalsMixin, 'perform_'+operation).__wrapped__
        method(QuotationDetailTotalsMixin(), instance if operation=='destroy' else serializer)
        lock.return_value.get.assert_called_once_with(pk=3)
        sync.assert_called_once_with(lock.return_value.get.return_value)
        (instance.delete if operation=='destroy' else serializer.save).assert_called_once()

def test_cannot_move_detail_to_another_quotation():
    serializer=SimpleNamespace(validated_data={'header_id':4},instance=SimpleNamespace(header_id=3))
    with pytest.raises(ValidationError):
        QuotationDetailTotalsMixin.perform_update.__wrapped__(QuotationDetailTotalsMixin(),serializer)
