import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
import django
django.setup()
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate
from ecf.customer_identity import validate_fiscal_id, customer_fiscal_status
from ecf.views import ECFCompanyViewSet


@pytest.mark.parametrize("kind,number,expected", [("R", "1-31-24679-6", "131246796"), ("C", "001-1391820-5", "00113918205"), ("R", "00113918205", "00113918205"), ("R", "101581601", "101581601")])
def test_fiscal_identity_accepts_checksummed_ids_and_known_legacy_exception(kind, number, expected):
    assert validate_fiscal_id(kind, number) == (kind, expected)


@pytest.mark.parametrize("kind,number", [("R", "131246795"), ("C", "00113918204"), ("C", "131246796"), ("R", "000000000"), ("C", "00000000000"), ("X", "131246796"), ("R", "131ABC246796"), ("R", ""), ("R", "١٣١٢٤٦٧٩٦")])
def test_invalid_or_wrong_type_ids_are_rejected(kind, number):
    with pytest.raises(ValueError):
        validate_fiscal_id(kind, number)


def customer(**changes):
    values = dict(pk=7, firstName="CLIENTE REAL", lastName="", identificationType="R", identification="131246796", save=MagicMock())
    values.update(changes)
    return SimpleNamespace(**values)


def test_valid_local_id_does_not_claim_official_dgii_registration_verification():
    result = customer_fiscal_status(customer())
    assert result["valid"] and not result["dgii_registration_verified"]
    assert result["validation"] == "format_checksum"


def test_shared_generic_customer_is_not_assigned_a_particular_tax_id():
    result = customer_fiscal_status(customer(firstName="GENÉRICO", lastName="CLIENTE"))
    assert not result["valid"] and "genérico" in result["message"]


def call_save(row, body):
    request = APIRequestFactory().post("/", body, format="json")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True, role="Caja", company_id=14))
    with patch("ecf.views.transaction.atomic"), patch("administration.models.Customer.objects.filter") as customers:
        customers.return_value.select_for_update.return_value.first.return_value = row
        response = ECFCompanyViewSet.as_view({"post": "customer_fiscal_id"})(request)
    return response, customers


def test_cashier_updates_only_fiscal_id_fields_within_own_company():
    row = customer(identification="", identificationType="")
    response, customers = call_save(row, {"customer": 7, "identificationType": "R", "identification": "1-31-24679-6", "company_id": 999, "firstName": "Do not overwrite"})
    assert response.status_code == 200 and response.data["valid"]
    customers.assert_called_once_with(pk=7, company_id=14)
    row.save.assert_called_once_with(update_fields=("identificationType", "identification"))
    assert row.identification == "131246796" and row.firstName == "CLIENTE REAL"


def test_invalid_update_does_not_overwrite_existing_customer_identity():
    row = customer()
    response, _ = call_save(row, {"customer": 7, "identificationType": "R", "identification": "131246795"})
    assert response.status_code == 400
    row.save.assert_not_called()
    assert row.identification == "131246796"


def test_other_company_customer_is_not_accessible():
    response, _ = call_save(None, {"customer": 7, "identificationType": "R", "identification": "131246796"})
    assert response.status_code == 400
