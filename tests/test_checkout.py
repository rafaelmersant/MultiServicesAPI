"""Checkout recovery/idempotency tests; no fiscal requests are transmitted."""
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from contextlib import ExitStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
import django
django.setup()
import pytest
from ecf.checkout import prepare_checkout, run_checkout
from ecf.workflow import ECFWorkflowError
from ecf.permissions import ECFCompanyAccessPermission


def fake_record(document_type="31"):
    pdf = MagicMock()
    pdf.__bool__.return_value = False
    pdf.save.side_effect = lambda *args, **kwargs: setattr(pdf.__bool__, "return_value", True)
    return SimpleNamespace(pk=1, status="draft", document_type=document_type, environment="prod", encf="", raw_xml="",
                           signed_xml="", xml_hash="", rfce_status="draft", track_id=None, representation_pdf=pdf,
                           save=MagicMock(), refresh_from_db=MagicMock())


def pipeline(record, query_status="accepted", send_error=None, claimed=True):
    stack = ExitStack()
    mocks = {}
    for name in ("_settings_for_record", "_reserve", "build_unsigned_xml", "sign_record", "send_record", "query_record_result",
                 "build_rfce_from_signed_ecf", "sign_rfce_record", "send_rfce_record", "build_representation_pdf"):
        mocks[name] = stack.enter_context(patch("ecf.checkout." + name))
    manager = stack.enter_context(patch("ecf.checkout.ElectronicInvoice.objects.filter"))
    manager.return_value.update.return_value = int(claimed)
    mocks["_reserve"].side_effect = lambda row: setattr(row, "encf", "E" + row.document_type + "0000000001")
    xml = b"<ECF><MontoTotal>100.00</MontoTotal></ECF>"
    mocks["build_unsigned_xml"].return_value = xml
    mocks["sign_record"].return_value = xml, "unit-test-hash"
    mocks["build_rfce_from_signed_ecf"].return_value = b"<RFCE/>"
    mocks["sign_rfce_record"].return_value = b"<RFCE/>"
    mocks["build_representation_pdf"].return_value = b"unit-test-pdf"
    def send(row):
        if send_error:
            row.status = "uncertain"
            raise ECFWorkflowError("Resultado incierto")
        row.status, row.track_id = "submitted", "test-track-id"
    mocks["send_record"].side_effect = send
    mocks["query_record_result"].side_effect = lambda row: setattr(row, "status", query_status)
    mocks["send_rfce_record"].side_effect = lambda row: setattr(row, "status", "accepted")
    return stack, mocks, manager


def test_normal_sale_uses_one_send_and_one_query_then_produces_pdf():
    record = fake_record()
    stack, mocks, manager = pipeline(record)
    with stack:
        run_checkout(record)
        run_checkout(record)  # A repeated request refers to the accepted record.
    assert record.status == "accepted"
    mocks["_reserve"].assert_called_once()
    mocks["send_record"].assert_called_once()
    mocks["query_record_result"].assert_called_once()
    mocks["build_representation_pdf"].assert_called_once()
    assert manager.return_value.update.call_args.kwargs == {"checkout_in_progress": False}


def test_small_e32_uses_rfce_instead_of_full_ecf_transport():
    record = fake_record("32")
    stack, mocks, _ = pipeline(record)
    with stack:
        run_checkout(record)
    mocks["send_rfce_record"].assert_called_once()
    mocks["send_record"].assert_not_called()
    assert record.status == "accepted"


def test_e32_at_threshold_uses_full_ecf_service():
    record = fake_record("32")
    stack, mocks, _ = pipeline(record)
    xml = b"<ECF><MontoTotal>250000.00</MontoTotal></ECF>"
    mocks["build_unsigned_xml"].return_value = xml
    mocks["sign_record"].return_value = xml, "unit-test-hash"
    with stack:
        run_checkout(record)
    mocks["send_record"].assert_called_once()
    mocks["send_rfce_record"].assert_not_called()


def test_processing_result_stays_pending_without_polling_loop_or_new_number():
    record = fake_record()
    stack, mocks, _ = pipeline(record, query_status="processing")
    with stack:
        run_checkout(record)
    assert record.status == "processing" and record.encf == "E310000000001"
    mocks["query_record_result"].assert_called_once()
    mocks["build_representation_pdf"].assert_not_called()


def test_uncertain_send_preserves_record_and_releases_automatic_claim():
    record = fake_record()
    stack, mocks, manager = pipeline(record, send_error=True)
    with stack:
        with pytest.raises(ECFWorkflowError, match="incierto"):
            run_checkout(record)
    assert record.status == "uncertain" and record.encf == "E310000000001"
    mocks["query_record_result"].assert_not_called()
    assert manager.return_value.update.call_args.kwargs == {"checkout_in_progress": False}


def test_double_click_does_not_start_parallel_fiscal_processing():
    record = fake_record()
    stack, mocks, _ = pipeline(record, claimed=False)
    with stack:
        assert "procesando" in run_checkout(record)
    mocks["_reserve"].assert_not_called()
    mocks["send_record"].assert_not_called()


def test_configuration_failure_leaves_draft_without_consuming_number():
    record = fake_record()
    stack, mocks, _ = pipeline(record)
    mocks["_settings_for_record"].side_effect = ECFWorkflowError("Ambiente incorrecto")
    with stack, pytest.raises(ECFWorkflowError):
        run_checkout(record)
    assert record.encf == "" and record.status == "draft"
    mocks["_reserve"].assert_not_called()


def test_retry_of_saved_sale_reuses_its_record_without_overwriting_payload():
    source = SimpleNamespace(ncf="")
    existing = SimpleNamespace(environment="prod", document_type="31")
    with patch("ecf.checkout.transaction.atomic"), patch("ecf.checkout.InvoicesHeader.objects.select_for_update") as invoices, patch("ecf.checkout.ElectronicInvoice.objects") as records:
        invoices.return_value.filter.return_value.first.return_value = source
        records.filter.return_value.first.return_value = existing
        assert prepare_checkout(1, 7, "31", {}) is existing
        records.create.assert_not_called()


def test_cashier_fallback_only_modifies_linked_production_sales_of_its_supported_types():
    permission = ECFCompanyAccessPermission()
    request = SimpleNamespace(method="POST", user=SimpleNamespace(is_authenticated=True, role="Caja"))
    assert permission.has_permission(request, SimpleNamespace(action="checkout_sale"))
    assert not permission.has_permission(request, SimpleNamespace(action="create"))
    assert permission.has_object_permission(request, None, SimpleNamespace(environment="prod", document_type="32", invoice_id=1))
    assert not permission.has_object_permission(request, None, SimpleNamespace(environment="cert", document_type="32", invoice_id=1))
    assert not permission.has_object_permission(request, None, SimpleNamespace(environment="prod", document_type="41", invoice_id=1))
