import os
from decimal import Decimal
from types import SimpleNamespace
import pytest
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MultiServices.settings')
import django
django.setup()
from products.serializers import ProductSerializer, ProductReducedSerializer
from rest_framework.exceptions import ValidationError

@pytest.mark.parametrize('serializer', [ProductSerializer, ProductReducedSerializer])
def test_rejects_tax_from_old_price(serializer):
    with pytest.raises(ValidationError):
        serializer().validate({'price': Decimal('9'), 'itbis': Decimal('1.983')})

@pytest.mark.parametrize('price,tax', [('9','1.373'), ('13','1.983'), ('9','0'), ('116','16')])
def test_consistent_inclusive_tax_and_untaxed(price, tax):
    attrs = {'price': Decimal(price), 'itbis': Decimal(tax)}
    assert ProductSerializer().validate(attrs) == attrs

def test_metadata_does_not_change_legacy_tax():
    old = SimpleNamespace(price=Decimal('9'), itbis=Decimal('1.983'))
    assert ProductSerializer(instance=old).validate({'description': 'PVC'}) == {'description': 'PVC'}

def test_price_only_update_cannot_leave_stale_tax():
    old = SimpleNamespace(price=Decimal('13'), itbis=Decimal('1.983'))
    with pytest.raises(ValidationError):
        ProductReducedSerializer(instance=old).validate({'price': Decimal('9')})
