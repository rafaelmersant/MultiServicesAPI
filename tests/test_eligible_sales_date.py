import os
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MultiServices.settings')
import django
django.setup()
from ecf.views import ECFCompanyViewSet
from rest_framework.exceptions import ValidationError

@pytest.mark.parametrize('start', ['2026-11-09', '', None])
def test_source_sale_date_filter(start):
    params={'environment':'prod'}
    if start is not None:
        params['start_date']=start
    request=SimpleNamespace(user=SimpleNamespace(company_id=14),query_params=params)
    rows=MagicMock()
    rows.exclude.return_value=rows
    rows.filter.return_value=rows
    rows.select_related.return_value=rows
    rows.order_by.return_value=rows
    rows.__getitem__.return_value=[]
    with patch('ecf.views.InvoicesHeader.objects.filter',return_value=rows):
        response=ECFCompanyViewSet().eligible_sales(request)
    assert response.data == []
    if start:
        rows.filter.assert_any_call(creationDate__date__gte=date(2026,11,9))
    else:
        assert all('creationDate__date__gte' not in call.kwargs for call in rows.filter.call_args_list)

def test_invalid_source_date():
    request=SimpleNamespace(user=SimpleNamespace(company_id=14),query_params={'start_date':'2026-99-09'})
    with patch('ecf.views.InvoicesHeader.objects.filter'),pytest.raises(ValidationError):
        ECFCompanyViewSet().eligible_sales(request)

