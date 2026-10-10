from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class TestCase:

    case_id: str
    version: str
    tipo_ecf: str
    encf: str

    values: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class TestSetSummary:

    ecf_cases: list[TestCase]

    rfce_cases: list[TestCase]

    @property
    def total(self) -> int:
        return (
            len(self.ecf_cases)
            + len(self.rfce_cases)
        )

    @property
    def counts_by_type(self) -> dict[str, int]:

        counts: dict[str, int] = {}

        for case in self.ecf_cases:

            counts[case.tipo_ecf] = (
                counts.get(case.tipo_ecf, 0) + 1
            )

        return counts


def decimal_or_none(
    value: Any
) -> Decimal | None:

    if value in (
        None,
        "",
        "#e"
    ):
        return None

    return Decimal(str(value))