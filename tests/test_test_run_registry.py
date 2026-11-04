from pathlib import Path

import pytest

from ecf.test_run_registry import (
    DuplicateECFError,
    ECFTestRegistry,
)


def test_reserve_blocks_duplicate_encf(tmp_path: Path):
    registry = ECFTestRegistry(tmp_path / "registry.sqlite3")
    registry.reserve_send(
        rnc="132018559",
        encf="E310000000007",
        case_id="132018559E310000000007",
        tipo_ecf="31",
        signed_xml=b"<ECF>test</ECF>",
    )
    with pytest.raises(DuplicateECFError):
        registry.reserve_send(
            rnc="132018559",
            encf="E310000000007",
            case_id="132018559E310000000007",
            tipo_ecf="31",
            signed_xml=b"<ECF>test</ECF>",
        )


def test_submission_and_result_are_persisted(tmp_path: Path):
    registry = ECFTestRegistry(tmp_path / "registry.sqlite3")
    registry.reserve_send(
        rnc="132018559",
        encf="E310000000007",
        case_id="132018559E310000000007",
        tipo_ecf="31",
        signed_xml=b"<ECF>test</ECF>",
    )
    registry.mark_submitted(
        rnc="132018559",
        encf="E310000000007",
        track_id="0868e251-3e96-419f-9899-9814dc003b49",
    )
    result = registry.mark_result(
        rnc="132018559",
        encf="E310000000007",
        code=1,
        status="Aceptado",
        sequence_used=True,
    )
    assert result.status == "accepted"
    assert result.track_id == "0868e251-3e96-419f-9899-9814dc003b49"
    assert result.sequence_used is True
    assert len(result.xml_sha256) == 64


def test_historical_record_blocks_future_send(tmp_path: Path):
    registry = ECFTestRegistry(tmp_path / "registry.sqlite3")
    registry.record_historical(
        rnc="132018559",
        encf="E310000000003",
        case_id="132018559E310000000003",
        tipo_ecf="31",
        status="accepted_conditional",
        dgii_code=4,
        dgii_status="Aceptado Condicional",
        track_id="f0673b51-3f9f-4f03-8c05-35b25a4af7ff",
        sequence_used=True,
    )
    with pytest.raises(DuplicateECFError):
        registry.reserve_send(
            rnc="132018559",
            encf="E310000000003",
            case_id="132018559E310000000003",
            tipo_ecf="31",
            signed_xml=b"<ECF>new</ECF>",
        )
