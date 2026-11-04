import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
import django

django.setup()

import pytest

from ecf.test_set_loader import CERTIFICATION_SEND_ORDER
from ecf.workflow import (
    ECFWorkflowError,
    _require_previous_certification_groups,
    _require_primary_groups_before_rfce,
)


def test_direct_api_send_is_blocked_until_prior_type_is_accepted():
    record = SimpleNamespace(
        payload={"certification_attempt": "attempt-1"},
        environment="cert",
        company_id=1,
        document_type="32",
    )
    with (
        patch("ecf.workflow.ElectronicInvoice.objects.filter"),
        patch("ecf.workflow._accepted_type_count", return_value=0),
        pytest.raises(ECFWorkflowError, match="tipo 31 aceptado 0/4"),
    ):
        _require_previous_certification_groups(record)


def test_rfce_api_send_is_blocked_until_all_primary_types_are_accepted():
    record = SimpleNamespace(
        payload={"certification_attempt": "attempt-1"},
        environment="cert",
        company_id=1,
    )
    with (
        patch("ecf.workflow.ElectronicInvoice.objects.filter"),
        patch("ecf.workflow._accepted_type_count", return_value=0),
        pytest.raises(ECFWorkflowError, match="tipo 31 aceptado 0/4"),
    ):
        _require_primary_groups_before_rfce(record)


def test_api_send_is_blocked_after_the_required_count_for_current_type_is_accepted():
    record = SimpleNamespace(
        payload={"certification_attempt": "attempt-1"},
        environment="cert",
        company_id=1,
        document_type="31",
    )
    with (
        patch("ecf.workflow.ElectronicInvoice.objects.filter"),
        patch("ecf.workflow._accepted_type_count", return_value=4),
        pytest.raises(ECFWorkflowError, match="tipo 31 ya tiene 4/4"),
    ):
        _require_previous_certification_groups(record)


def test_certification_send_order_matches_dgii_portal_sequence():
    assert CERTIFICATION_SEND_ORDER == ("31", "32", "41", "43", "44", "45", "46", "47", "33", "34")
