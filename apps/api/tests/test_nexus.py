import json

import httpx
import pytest

from app.core.config import Settings
from app.integrations.nexus import MAX_RESPONSE_BYTES, NexusConnector, NexusReadError


def settings(**kwargs) -> Settings:
    return Settings(
        database_url="sqlite://",
        nexus_email="reader@example.test",
        nexus_password="private-test-value",
        nexus_page_size=1,
        nexus_max_pages=2,
        _env_file=None,
        **kwargs,
    )


def login_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={"success": True, "user": {"private": "not-exported"}},
        headers={"Set-Cookie": "auth-token=test-only; Path=/; Secure; HttpOnly"},
    )


def equipment_page(number=1, total=1, identifier="eq-1") -> dict:
    return {
        "items": [
            {
                "id": identifier,
                "clave": "RE-03",
                "nombre": "Retroexcavadora",
                "estado": "DISPONIBLE",
                "unknown_private_field": "never-retained",
            }
        ],
        "total": total,
        "page": number,
        "limit": 1,
    }


def empty_requests() -> httpx.Response:
    return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "limit": 1})


def test_cookie_reuse_and_only_observed_routes_are_called():
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.path == "/api/auth/login":
            assert json.loads(request.content)["email"] == "reader@example.test"
            return login_response()
        assert request.headers["cookie"] == "auth-token=test-only"
        if request.url.path.endswith("equipos"):
            return httpx.Response(200, json=equipment_page())
        return empty_requests()

    connector = NexusConnector(settings(), transport=httpx.MockTransport(handler))
    try:
        first = connector.read()
        connector.read()
    finally:
        connector.close()
    assert first.complete is True
    assert not hasattr(first.equipment[0], "unknown_private_field")
    assert calls.count(("POST", "/api/auth/login")) == 1
    assert set(calls) == {
        ("POST", "/api/auth/login"),
        ("GET", "/api/maquinaria/equipos"),
        ("GET", "/api/maquinaria/requests"),
    }


@pytest.mark.parametrize("after_retry", [200, 401])
def test_401_reauthenticates_once_and_repeats_safe_read_at_most_once(after_retry):
    logins = reads = 0

    def handler(request):
        nonlocal logins, reads
        if request.method == "POST":
            logins += 1
            return login_response()
        if request.url.path.endswith("equipos"):
            reads += 1
            status = 401 if reads == 1 else after_retry
            return httpx.Response(status, json=equipment_page())
        return empty_requests()

    connector = NexusConnector(settings(), transport=httpx.MockTransport(handler))
    try:
        if after_retry == 200:
            assert connector.read().complete
        else:
            with pytest.raises(NexusReadError, match="después de reautenticar"):
                connector.read()
    finally:
        connector.close()
    assert logins == reads == 2


@pytest.mark.parametrize("status", [403, 429, 500, 302])
def test_access_errors_are_not_retried_and_upstream_details_are_hidden(status):
    calls = []

    def handler(request):
        calls.append(request.method)
        if request.method == "POST":
            return login_response()
        return httpx.Response(status, text="private-test-value server details")

    connector = NexusConnector(settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(NexusReadError) as caught:
            connector.read()
    finally:
        connector.close()
    assert calls == ["POST", "GET"]
    assert "private-test-value" not in str(caught.value)


def test_bounded_pages_and_duplicate_ids_are_partial():
    def handler(request):
        if request.method == "POST":
            return login_response()
        if request.url.path.endswith("requests"):
            return empty_requests()
        page = int(request.url.params["page"])
        return httpx.Response(200, json=equipment_page(number=page, total=100))

    connector = NexusConnector(settings(), transport=httpx.MockTransport(handler))
    try:
        data = connector.read()
    finally:
        connector.close()
    assert data.equipment_total == 100
    assert len(data.equipment) == 1  # Same ID on both pages is never double counted.
    assert data.complete is False


@pytest.mark.parametrize(
    "payload",
    [
        {"items": [], "total": "1", "page": 1, "limit": 1},
        {"items": [{"id": "x"}], "total": 1, "page": 1, "limit": 1},
        {"items": [], "total": 0, "page": 99, "limit": 1},
        {"items": [], "total": 0, "page": 1, "limit": 100},
        {"error": "private-test-value"},
    ],
)
def test_schema_drift_is_an_error_not_an_empty_success(payload):
    def handler(request):
        return login_response() if request.method == "POST" else httpx.Response(200, json=payload)

    connector = NexusConnector(settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(NexusReadError) as caught:
            connector.read()
    finally:
        connector.close()
    assert "private-test-value" not in str(caught.value)


def test_failed_requests_collection_does_not_return_a_complete_equipment_snapshot():
    def handler(request):
        if request.method == "POST":
            return login_response()
        if request.url.path.endswith("equipos"):
            return httpx.Response(200, json=equipment_page())
        return httpx.Response(403)

    connector = NexusConnector(settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(NexusReadError, match="permiso"):
            connector.read()
    finally:
        connector.close()


def test_response_size_limit_and_settings_hide_secrets():
    def handler(request):
        if request.method == "POST":
            return login_response()
        return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))

    configuration = settings()
    assert "private-test-value" not in repr(configuration)
    connector = NexusConnector(configuration, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(NexusReadError, match="tamaño"):
            connector.read()
    finally:
        connector.close()


def test_empty_secret_is_not_configured():
    configuration = settings()
    configuration.nexus_password = None
    connector = NexusConnector(configuration)
    try:
        assert connector.configured is False
    finally:
        connector.close()


def test_nullable_equipment_code_from_observed_sandbox_response():
    def handler(request):
        if request.method == "POST":
            return login_response()
        if request.url.path.endswith("requests"):
            return empty_requests()
        payload = equipment_page()
        payload["items"][0].update({"clave": None, "no_activo": "fixture:asset-01"})
        return httpx.Response(200, json=payload)

    connector = NexusConnector(settings(), transport=httpx.MockTransport(handler))
    try:
        data = connector.read()
    finally:
        connector.close()
    assert data.equipment[0].clave is None
    assert data.equipment[0].no_activo == "fixture:asset-01"


def test_timeout_and_total_read_budget_are_bounded():
    from unittest.mock import patch

    def handler(request):
        raise httpx.ReadTimeout("private-test-value", request=request)

    connector = NexusConnector(settings(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(NexusReadError) as caught:
            connector.read()
        assert "private-test-value" not in str(caught.value)
        with patch("app.integrations.http.monotonic", side_effect=[0, 30]):
            with pytest.raises(NexusReadError, match="tiempo permitido"):
                connector.read()
    finally:
        connector.close()


@pytest.mark.parametrize("kind", ["request", "equipment"])
def test_exact_detail_gets_only_documented_route_and_keeps_nullable_fields(kind):
    identifier = "46d2573e-08d3-4855-971d-2fbf9564e135"

    def handler(request):
        if request.method == "POST":
            return login_response()
        expected = "requests" if kind == "request" else "equipos"
        assert request.url.path == f"/api/maquinaria/{expected}/{identifier}"
        assert not request.url.query
        data = (
            {
                "id": identifier,
                "status": "APROBADA",
                "maquinaria_id": None,
                "fecha_inicio": "2026-09-12",
                "approved_at": "2026-09-12T01:00:01.535958+00:00",
            }
            if kind == "request"
            else {
                "id": identifier,
                "clave": None,
                "no_activo": "RE-03",
                "nombre": "Retroexcavadora",
                "estado": "OCUPADA",
                "active_failure_is_paro": None,
            }
        )
        return httpx.Response(200, json=data)

    connector = NexusConnector(settings(), httpx.MockTransport(handler))
    try:
        item = getattr(connector, f"get_{kind}")(identifier)
    finally:
        connector.close()
    assert item.id == identifier
    if kind == "request":
        assert item.maquinaria_id is None and item.fecha_inicio == "2026-09-12"
        assert item.approved_at.microsecond == 535958 and item.approved_at.tzinfo is not None
    else:
        assert item.clave is None and item.active_failure_is_paro is None


@pytest.mark.parametrize("identifier", ["", "not-a-uuid", "../projects", "https://evil.test"])
def test_detail_invalid_ids_never_contact_nexus(identifier):
    calls = []
    connector = NexusConnector(
        settings(), httpx.MockTransport(lambda request: calls.append(request))
    )
    try:
        with pytest.raises(NexusReadError, match="UUID"):
            connector.get_request(identifier)
    finally:
        connector.close()
    assert calls == []


def test_detail_id_mismatch_and_missing_upstream_are_explicit_errors():
    identifier = "46d2573e-08d3-4855-971d-2fbf9564e135"
    responses = [
        httpx.Response(200, json={"id": "another-request", "status": "APROBADA"}),
        httpx.Response(404, text="private-test-value"),
    ]

    def handler(request):
        return login_response() if request.method == "POST" else responses.pop(0)

    connector = NexusConnector(settings(), httpx.MockTransport(handler))
    try:
        with pytest.raises(NexusReadError, match="ID distinto"):
            connector.get_request(identifier)
        with pytest.raises(NexusReadError) as caught:
            connector.get_request(identifier)
    finally:
        connector.close()
    assert "private-test-value" not in str(caught.value)


def test_to_records_keeps_documented_assignment_operator_and_rate_fields():
    """Documented fields are projected by ID; a list read leaves detail-only ones unread."""
    from app.integrations.nexus import NexusEquipment, NexusRequest, to_records
    from app.models.hub import Provenance

    def provenance(collection, index, source_id):
        return Provenance(
            source="nexus",
            source_id=source_id,
            environment="sandbox",
            observed_at=None,
            is_synthetic=True,
            evidence_kind="live_read",
        )

    detail = NexusEquipment.model_validate(
        {
            "id": "66faacde",
            "clave": None,
            "no_activo": "CF-03",
            "nombre": "Cargador frontal 03",
            "estado": "OBSOLETA",
            "project_id": "39723f32",
            "fecha_inicio_uso": "2026-09-11",
            "fecha_fin_uso": "2026-09-14",
            "observaciones_asignacion": "Solicitud aprobada: Cargador frontal",
            "associated_operators": [
                {"id": "7753f3fe", "nombre": "Carlos Herrera", "cod_trabajador": "MOT-015"}
            ],
            "current_project_rate": {
                "project_id": "39723f32",
                "precio_x_hora": 45,
                "effective_from": "2026-09-11",
            },
        }
    )
    listed = NexusEquipment.model_validate(
        {
            "id": "2a49b73e",
            "clave": None,
            "no_activo": "CF-01",
            "nombre": "Cargador frontal 01",
            "estado": "DISPONIBLE",
        }
    )
    request = NexusRequest.model_validate(
        {
            "id": "req-1",
            "tipo": "Cargador frontal",
            "status": "APROBADA",
            "maquinaria_id": "66faacde",
            "maquinaria_nombre": "Cargador frontal 03",
            "maquinaria_no_activo": "CF-03",
            "approved_by_user_id": "98bf9d4d",
            "approved_by_name": "María José López Ramírez",
        }
    )

    equipment, requests = to_records([detail, listed], [request], provenance, "note")

    unit = equipment[0]
    assert unit.assignment_starts_on == "2026-09-11"
    assert unit.assignment_note == "Solicitud aprobada: Cargador frontal"
    assert [op.worker_code for op in unit.operators] == ["MOT-015"]
    assert unit.project_rate.project_id == "39723f32"
    assert unit.project_rate.hourly_rate == 45
    assert equipment[1].operators is None
    assert equipment[1].project_rate is None
    assert requests[0].machinery_asset_number == "CF-03"
    assert requests[0].approved_by == "María José López Ramírez"
    assert requests[0].machinery_id == "nexus:equipment:66faacde"
