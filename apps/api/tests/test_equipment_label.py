"""Verify the display-label policy with the actual sandbox samples and edge cases.

CF-01 has clave='-' and no_activo='CF-01': the label must be 'CF-01', never '-'.
CF-02 has clave='200' and no_activo='CF-02': the label must be 'CF-02', never '200'.
The same label feeds the Startrack draft objective; a regression here sends an
unreadable objective to the provider.
"""

import pytest

from app.dashboard.analytics import equipment_label
from app.models.hub import EquipmentRecord, Provenance, RequestRecord
from app.services.transfers import TransferMapping, prepare_transfer

OBSERVED_ON = "2026-09-12"


def _provenance(source_id: str) -> Provenance:
    return Provenance(
        source="nexus",
        source_id=source_id,
        environment="sandbox",
        observed_at=None,
        is_synthetic=True,
        evidence_kind="provided_sample",
        observed_on=OBSERVED_ON,
    )


def _equipment(
    asset_number: str | None, code: str | None, name: str, source_id: str = "test-unit"
) -> EquipmentRecord:
    return EquipmentRecord(
        id=f"nexus:equipment:{source_id}",
        code=code,
        asset_number=asset_number,
        name=name,
        machinery_status="OCUPADA",
        maintenance_is_stopped=False,
        relation_status="unlinked",
        relation_note="Test input only.",
        provenance=_provenance(source_id),
    )


def _request(machinery_source_id: str = "test-unit") -> RequestRecord:
    return RequestRecord(
        id="nexus:request:test-request",
        status="APROBADA",
        machinery_id=f"nexus:equipment:{machinery_source_id}",
        project_id="test-project",
        project_name="Proyecto de prueba",
        starts_on="2026-09-01",
        provenance=_provenance("test-request"),
    )


def _mapping(machinery_source_id: str = "test-unit") -> TransferMapping:
    return TransferMapping(
        request_source_id="test-request",
        machinery_source_id=machinery_source_id,
        project_source_id="test-project",
        poi_id="test-poi",
        assigned_user_ids=("test-user",),
        movement_reference="test-movement",
        scheduled_date="2026-09-14",
    )


# ------------------------------------------------------------------
# Parametrized regression: sandbox samples and edge cases
# ------------------------------------------------------------------
@pytest.mark.parametrize(
    "asset_number,code,name,expected_label",
    [
        # Real sandbox samples
        ("CF-01", "-", "Cargador frontal 01", "CF-01"),
        ("CF-02", "200", "Cargador frontal 02", "CF-02"),
        ("CF-03", None, "Cargador frontal 03", "CF-03"),
        ("EXC-01", None, "Excavadora 01", "EXC-01"),
        # Edge cases
        (None, "EXC-CODE", "Excavadora 01", "EXC-CODE"),
        (None, None, "Retroexcavadora 01", "Retroexcavadora 01"),
    ],
    ids=[
        "CF-01_clave_dash",
        "CF-02_clave_200",
        "CF-03_clave_none",
        "EXC-01_clave_none",
        "no_asset_with_code",
        "name_only_fallback",
    ],
)
def test_equipment_label_uses_asset_number_over_code(asset_number, code, name, expected_label):
    equipment = _equipment(asset_number, code, name)
    assert equipment_label(equipment) == expected_label


@pytest.mark.parametrize(
    "asset_number,code,name,expected_label",
    [
        ("CF-01", "-", "Cargador frontal 01", "CF-01"),
        ("CF-02", "200", "Cargador frontal 02", "CF-02"),
        (None, "EXC-CODE", "Excavadora 01", "EXC-CODE"),
        (None, None, "Retroexcavadora 01", "Retroexcavadora 01"),
    ],
    ids=[
        "CF-01_objective",
        "CF-02_objective",
        "code_fallback_objective",
        "name_fallback_objective",
    ],
)
def test_draft_objective_uses_correct_label_not_raw_code(asset_number, code, name, expected_label):
    equipment = _equipment(asset_number, code, name)
    request = _request()
    mapping = _mapping()
    preparation = prepare_transfer(request, equipment, mapping)
    assert preparation.status == "draft_prepared"
    assert preparation.draft is not None
    assert preparation.draft.objective.startswith(f"Traslado de {expected_label} a")


def test_cf01_objective_never_contains_dash_as_label():
    """CF-01 with clave='-' must never produce 'Traslado de - a ...'."""
    equipment = _equipment("CF-01", "-", "Cargador frontal 01")
    request = _request()
    mapping = _mapping()
    preparation = prepare_transfer(request, equipment, mapping)
    assert preparation.draft is not None
    assert not preparation.draft.objective.startswith("Traslado de - ")
    assert not preparation.draft.objective.startswith("Traslado de -\t")


def test_cf02_objective_never_contains_200_as_label():
    """CF-02 with clave='200' must never produce 'Traslado de 200 a ...'."""
    equipment = _equipment("CF-02", "200", "Cargador frontal 02")
    request = _request()
    mapping = _mapping()
    preparation = prepare_transfer(request, equipment, mapping)
    assert preparation.draft is not None
    assert not preparation.draft.objective.startswith("Traslado de 200 ")
