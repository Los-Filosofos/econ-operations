import base64
import json
from datetime import UTC, date, datetime
from urllib.parse import parse_qs

import httpx
import pytest
from pydantic import ValidationError

from app.integrations.startrack import (
    MAX_RESPONSE_BYTES,
    StartrackClient,
    StartrackReadConfig,
    StartrackReadError,
    StartrackTaskDraft,
    StartrackWriteRejected,
    StartrackWriteUnknown,
)


def config(**changes) -> StartrackReadConfig:
    values = {
        "enabled": True,
        "api_key": "test-api-key",
        "password": "private-test-password",
        "page_size": 2,
        "max_pages": 2,
    }
    return StartrackReadConfig(**(values | changes))


def job(identifier="task-1", **changes) -> dict:
    return {
        "id": identifier,
        "objective": "Traslado de equipo",
        "start_date": "2026-09-14",
        "status": "1",
        "remote_id": "request-1",
        "poi_id": "poi-1",
        "closed_date": "2026-09-14 08:00:00-06:00",
    } | changes


def draft(**changes) -> StartrackTaskDraft:
    values = {
        "objective": "Traslado de equipo",
        "start_date": "2026-09-14",
        "remote_id": "request-1:assignment-1",
        "poi_id": "poi-1",
        "assigned_user_ids": ["user-1"],
    }
    return StartrackTaskDraft(**(values | changes))


@pytest.mark.parametrize(
    "options", [StartrackReadConfig(), config(enabled=False), config(api_key=None)]
)
def test_disabled_or_unconfigured_client_never_contacts_provider(options):
    calls = []
    client = StartrackClient(
        options, transport=httpx.MockTransport(lambda request: calls.append(request))
    )
    try:
        with pytest.raises(StartrackReadError):
            client.list_jobs()
    finally:
        client.close()
    assert calls == []


def test_fixed_origin_basic_auth_explicit_read_routes_and_source_fields():
    calls = []
    expected_auth = base64.b64encode(b"test-api-key:private-test-password").decode()

    def handler(request):
        calls.append(request.url.path)
        assert request.method == "GET"
        assert str(request.url).startswith("https://staging.gps.gt/api/")
        assert "private-test-password" not in str(request.url)
        assert request.headers["Authorization"] == f"Basic {expected_auth}"
        assert request.url.params["page_num"] == "0"
        assert request.url.params["page_size"] == "2"
        assert request.url.params["sort_by"] == "id"
        assert "phone_number" not in request.url.params["fields"]
        data = (
            job(private_field="must-not-be-retained")
            if request.url.path == "/api/job"
            else {"id": "poi-1", "name": "Destino", "remote_id": "project-1"}
        )
        return httpx.Response(200, json={"success": True, "data": [data]})

    before = datetime.now(UTC)
    client = StartrackClient(config(), transport=httpx.MockTransport(handler))
    try:
        jobs = client.list_jobs()
        pois = client.list_pois()
    finally:
        client.close()
    assert calls == ["/api/job", "/api/pois"]
    assert jobs.items[0].id == "task-1"
    assert jobs.items[0].closed_date == "2026-09-14 08:00:00-06:00"
    assert jobs.items[0].status == "1"  # Provider state is not converted into receipt.
    assert not hasattr(jobs.items[0], "private_field")
    assert not hasattr(jobs.items[0], "received_at")
    assert jobs.environment == "sandbox" and jobs.is_synthetic is True
    assert jobs.exhausted and not jobs.complete
    assert before <= jobs.observed_at <= datetime.now(UTC)
    assert pois.items[0].remote_id == "project-1"


@pytest.mark.parametrize("status", [401, 403, 429, 529, 302, 500])
def test_errors_are_sanitized_with_no_retries_or_redirects(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            text="private-test-password provider details",
            headers={"Location": "https://other.example.test/private-test-password"},
        )

    client = StartrackClient(config(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(StartrackReadError) as caught:
            client.list_jobs()
    finally:
        client.close()
    assert len(calls) == 1
    assert "private-test-password" not in str(caught.value)
    assert "other.example" not in str(caught.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"success": "true", "data": []},
        {"success": False, "data": []},
        {"success": True},
        {"success": True, "data": {}},
        {"success": True, "data": [{"id": "task-1"}]},
        {"success": True, "data": [job(identifier=" ")]},
        {"success": True, "data": [job(identifier=123)]},
        {"error": "private-test-password"},
    ],
)
def test_schema_drift_is_visible_instead_of_empty_success(payload):
    client = StartrackClient(
        config(), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    try:
        with pytest.raises(StartrackReadError) as caught:
            client.list_jobs()
    finally:
        client.close()
    assert "private-test-password" not in str(caught.value)


def test_full_pages_are_bounded_and_remote_id_is_not_assumed_unique():
    pages = []

    def handler(request):
        page = int(request.url.params["page_num"])
        pages.append(page)
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [job(f"task-{page}-a"), job(f"task-{page}-b")],
            },
        )

    client = StartrackClient(config(), transport=httpx.MockTransport(handler))
    try:
        result = client.list_jobs()
    finally:
        client.close()
    assert pages == [0, 1]
    assert result.pages_read == 2
    assert len(result.items) == 4
    assert {item.remote_id for item in result.items} == {"request-1"}
    assert not result.exhausted and not result.complete


def test_unknown_status_and_exact_ids_are_preserved_with_writes_disabled():
    def handler(request):
        assert request.method == "GET"
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    job(
                        identifier="000042",
                        status="provider-new-status",
                        remote_id="000007",
                        poi_id="000011",
                        assigned_user_ids=["000003"],
                    )
                ],
            },
        )

    client = StartrackClient(config(), transport=httpx.MockTransport(handler))
    try:
        result = client.list_jobs()
    finally:
        client.close()
    item = result.items[0]
    assert (item.id, item.remote_id, item.poi_id) == ("000042", "000007", "000011")
    assert item.assigned_user_ids == ["000003"]
    assert item.status == "provider-new-status"
    assert client.config.allow_writes is False


@pytest.mark.parametrize(
    "failure", ["duplicate", "oversized-page", "oversized-body", "invalid-json"]
)
def test_inconsistent_or_oversized_reads_fail_explicitly(failure):
    def handler(request):
        if failure == "oversized-body":
            return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))
        if failure == "invalid-json":
            return httpx.Response(200, content=b"private-test-password invalid JSON")
        count = 3 if failure == "oversized-page" else 2
        return httpx.Response(
            200,
            json={"success": True, "data": [job(f"task-{number}") for number in range(count)]},
        )

    client = StartrackClient(config(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(StartrackReadError) as caught:
            client.list_jobs()
    finally:
        client.close()
    assert "private-test-password" not in str(caught.value)


def test_http_timeout_is_sanitized():
    def handler(request):
        raise httpx.ReadTimeout("private-test-password", request=request)

    client = StartrackClient(config(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(StartrackReadError) as caught:
            client.list_jobs()
    finally:
        client.close()
    assert "private-test-password" not in str(caught.value)


def test_overall_budget_is_checked_after_response_and_lock_is_released(monkeypatch):
    now = [0.0]
    monkeypatch.setattr("app.integrations.startrack.monotonic", lambda: now[0])

    def handler(request):
        now[0] += 2
        return httpx.Response(200, json={"success": True, "data": []})

    client = StartrackClient(config(budget_seconds=1), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(StartrackReadError, match="superó el tiempo"):
            client.list_jobs()
        assert client._lock.acquire(blocking=False)
        client._lock.release()
    finally:
        client.close()


def test_configuration_repr_and_serialization_exclude_credentials():
    options = config()
    for output in (repr(options), options.model_dump_json()):
        assert "test-api-key" not in output
        assert "private-test-password" not in output


def test_task_draft_contains_only_explicit_documented_fields_and_disables_notifications():
    task = draft()
    assert task.payload() == {
        "objective": "Traslado de equipo",
        "start_date": "2026-09-14",
        "remote_id": "request-1:assignment-1",
        "poi_id": "poi-1",
        "assigned_user_ids": ["user-1"],
        "notify_contact": False,
    }
    assert (
        draft(start_date=date(2026, 9, 14), start_time="08:30:00").payload()["start_time"]
        == "08:30:00"
    )
    description = "Proyecto: project-1; solicitud: request-1; equipo: equipment-1"
    assert draft(description=description).payload()["description"] == description


@pytest.mark.parametrize(
    "changes",
    [
        {"objective": " "},
        {"objective": "x" * 256},
        {"start_date": None},
        {"start_date": 1789344000},
        {"start_date": "20260914"},
        {"start_date": "2026-09-14T00:00:00Z"},
        {"start_date": datetime(2026, 9, 14, tzinfo=UTC)},
        {"remote_id": ""},
        {"poi_id": " "},
        {"assigned_user_ids": []},
        {"assigned_user_ids": ["user-1", "user-1"]},
        {"assigned_user_ids": [123]},
        {"start_time": "25:00:00"},
        {"notify_contact": True},
        {"completed_lat": "13.6"},
        {"received_at": "2026-09-14"},
    ],
)
def test_task_draft_rejects_missing_ambiguous_or_undocumented_inputs(changes):
    with pytest.raises(ValidationError):
        draft(**changes)


@pytest.mark.parametrize(
    "options", [StartrackReadConfig(), config(), config(allow_writes=True, api_key=None)]
)
def test_create_is_independently_disabled_and_never_contacts_provider(options):
    calls = []
    client = StartrackClient(options, httpx.MockTransport(lambda request: calls.append(request)))
    try:
        with pytest.raises(StartrackWriteRejected):
            client.create_job(draft())
    finally:
        client.close()
    assert calls == []


def test_create_posts_form_encoded_arrays_once_without_notifications_or_read_gate():
    calls = []
    task = draft(form_ids=["123", "004"], required_form_ids=["123"])

    def handler(request):
        calls.append(request)
        assert request.method == "POST" and request.url.path == "/api/job"
        assert request.url.host == "staging.gps.gt"
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert not request.url.query
        body = parse_qs(request.content.decode())
        assert body["notify_contact"] == ["0"]
        assert json.loads(body["assigned_user_ids"][0]) == ["user-1"]
        assert json.loads(body["form_ids"][0]) == ["123", "004"]
        assert json.loads(body["required_form_ids"][0]) == ["123"]
        assert body["remote_id"] == [task.remote_id]
        assert "contact_email" not in body and "notification_emails_csv" not in body
        return httpx.Response(201, json={"success": True, "data": job(remote_id=task.remote_id)})

    client = StartrackClient(config(enabled=False, allow_writes=True), httpx.MockTransport(handler))
    try:
        assert client.create_job(task).id == "task-1"
    finally:
        client.close()
    assert len(calls) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422, 429])
def test_confirmed_create_rejection_does_not_retry_or_expose_response(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="private-test-password upstream details")

    client = StartrackClient(config(allow_writes=True), httpx.MockTransport(handler))
    try:
        with pytest.raises(StartrackWriteRejected) as caught:
            client.create_job(draft())
    finally:
        client.close()
    assert len(calls) == 1
    assert "private-test-password" not in str(caught.value)


@pytest.mark.parametrize(
    "outcome",
    [
        "timeout",
        "connection",
        302,
        408,
        500,
        502,
        503,
        529,
        "malformed",
        "missing-id",
        "wrong-remote-id",
        "nonboolean-success",
        "oversized",
        "contradictory",
    ],
)
def test_uncertain_create_outcome_never_retries_or_claims_rejection(outcome):
    calls = []

    def handler(request):
        calls.append(request)
        if outcome == "timeout":
            raise httpx.ReadTimeout("private-test-password", request=request)
        if outcome == "connection":
            raise httpx.ConnectError("private-test-password", request=request)
        if isinstance(outcome, int):
            return httpx.Response(
                outcome,
                text="private-test-password",
                headers={"Location": "https://other.example.test/private-test-password"},
            )
        if outcome == "malformed":
            return httpx.Response(200, text="private-test-password")
        if outcome == "oversized":
            return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))
        if outcome == "missing-id":
            return httpx.Response(200, json={"success": True, "data": {"objective": "x"}})
        if outcome == "contradictory":
            return httpx.Response(200, json={"success": False, "data": job()})
        return httpx.Response(
            200,
            json={
                "success": "true" if outcome == "nonboolean-success" else True,
                "data": job(remote_id="other-remote-id"),
            },
        )

    client = StartrackClient(config(allow_writes=True), httpx.MockTransport(handler))
    try:
        with pytest.raises(StartrackWriteUnknown) as caught:
            client.create_job(draft())
        assert client._lock.acquire(blocking=False)
        client._lock.release()
    finally:
        client.close()
    assert len(calls) == 1
    assert "private-test-password" not in str(caught.value)
    assert "other.example" not in str(caught.value)


def test_explicit_application_rejection_and_missing_optional_remote_id():
    responses = [
        {"success": False, "error": "private-test-password"},
        {"success": True, "data": job(remote_id=None)},
    ]
    client = StartrackClient(
        config(allow_writes=True),
        httpx.MockTransport(lambda _: httpx.Response(200, json=responses.pop(0))),
    )
    try:
        with pytest.raises(StartrackWriteRejected):
            client.create_job(draft())
        assert client.create_job(draft()).remote_id is None
    finally:
        client.close()


def test_unvalidated_model_updates_cannot_enable_contact_notification():
    calls = []
    client = StartrackClient(
        config(allow_writes=True), httpx.MockTransport(lambda request: calls.append(request))
    )
    try:
        with pytest.raises(StartrackWriteRejected):
            client.create_job(draft().model_copy(update={"notify_contact": True}))
    finally:
        client.close()
    assert calls == []


def test_documented_catalog_routes_and_unpaged_users_drop_private_fields():
    def handler(request):
        assert request.method == "GET"
        path = request.url.path
        if path == "/api/user":
            assert not request.url.query
            record = {"id": "001", "name": "Operador", "email": "private@example.test"}
        elif path == "/api/vehicles":
            assert set(request.url.params) == {"page_num", "page_size"}
            record = {"id": "002", "description": "Transportador", "vin": "remote-vin"}
        elif path == "/api/job/status":
            record = {"id": "003", "name": "Finalizada", "workflow_role": "1"}
        else:
            assert path == "/api/job/type"
            record = {"id": 4, "name": "Traslado"}
        return httpx.Response(200, json={"success": True, "data": [record]})

    client = StartrackClient(config(), httpx.MockTransport(handler))
    try:
        users = client.list_users()
        assert users.items[0].id == "001" and not hasattr(users.items[0], "email")
        assert not users.complete and not users.exhausted
        assert client.list_vehicles().items[0].vin == "remote-vin"
        assert client.list_job_statuses().items[0].workflow_role == "1"
        assert client.list_job_types().items[0].id == "4"
    finally:
        client.close()


def test_remote_id_lookup_uses_documented_exact_filters_and_keeps_ambiguous_matches():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.path == "/api/job"
        assert request.url.params["filter_by"] == "remote_id"
        assert request.url.params["filter_values"] == "movement-1"
        assert request.url.params["filter_comp"] == "equal"
        records = (
            []
            if request.url.params["page_num"] == "1"
            else [job("1", remote_id="movement-1"), job("2", remote_id="movement-1")]
        )
        return httpx.Response(200, json={"success": True, "data": records})

    client = StartrackClient(config(), httpx.MockTransport(handler))
    try:
        result = client.find_jobs_by_remote_id("movement-1")
        assert [item.id for item in result.items] == ["1", "2"]
        assert not result.complete
        with pytest.raises(StartrackReadError):
            client.find_jobs_by_remote_id("remote|id")
    finally:
        client.close()
    assert len(calls) == 2


def test_exact_job_read_rejects_ignored_filters_and_returns_missing_explicitly():
    data = [[job("other")], [], [job("000042")]]

    def handler(request):
        assert request.url.params["filter_by"] == "id"
        assert request.url.params["filter_values"] == "000042"
        return httpx.Response(200, json={"success": True, "data": data.pop(0)})

    client = StartrackClient(config(), httpx.MockTransport(handler))
    try:
        with pytest.raises(StartrackReadError):
            client.get_job("000042")
        assert client.get_job("000042") is None
        assert client.get_job("000042").id == "000042"
    finally:
        client.close()


def test_visits_preserve_original_event_instants_and_scope_without_invented_pagination():
    def handler(request):
        assert request.url.path == "/api/visits"
        assert request.url.params["pois"] == "520"
        assert request.url.params["vehicle_ids"] == "344"
        assert request.url.params["findby"] == "veh"
        assert request.url.params["start_time"] == "00:00:00"
        assert request.url.params["end_time"] == "23:59:59"
        assert "page_size" not in request.url.params and "fields" not in request.url.params
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {
                        "id": 23456,
                        "vehicle_id": 344,
                        "poi_id": 520,
                        "start_date": "2026-09-12T08:03:47-06:00",
                        "end_date": None,
                    }
                ],
            },
        )

    client = StartrackClient(config(), httpx.MockTransport(handler))
    try:
        result = client.list_visits(
            start_date=date(2026, 9, 12),
            end_date=date(2026, 9, 12),
            poi_ids=("520",),
            vehicle_ids=("344",),
        )
    finally:
        client.close()
    assert result.items[0].id == "23456"
    assert result.items[0].start_date == "2026-09-12T08:03:47-06:00"
    assert result.items[0].end_date is None
    assert not result.complete and not hasattr(result.items[0], "received_at")


def test_form_responses_preserve_epoch_and_nested_task_and_question_ids():
    def handler(request):
        assert request.url.path == "/api/form-responses"
        assert request.url.params["form_id"] == "1483"
        assert request.url.params["job_id"] == "42"
        return httpx.Response(
            200,
            json={
                "success": True,
                "responses": [
                    {
                        "id": 3759,
                        "user_id": "214",
                        "date": 1789224000,
                        "server_date": 1789224050,
                        "gps_epoch": 1789223995,
                        "job": {"id": "42", "remote_id": "movement-1", "title": "Traslado"},
                        "poi": {"id": 520, "name": "Destino"},
                        "1": "Revisado",
                        "2": ["observacion"],
                        "undocumented": "private-test-value",
                    }
                ],
            },
        )

    client = StartrackClient(config(), httpx.MockTransport(handler))
    try:
        result = client.list_form_responses(
            form_id="1483",
            job_id="42",
            start_date=date(2026, 9, 12),
            end_date=date(2026, 9, 12),
        )
    finally:
        client.close()
    item = result.items[0]
    assert item.id == "3759" and item.date == 1789224000 and item.gps_epoch == 1789223995
    assert item.job.id == "42" and item.poi.id == "520"
    assert item.answers == {"1": "Revisado", "2": ["observacion"]}
    assert type(item).model_validate_json(item.model_dump_json()).answers == item.answers
    assert not hasattr(item, "undocumented") and not result.complete


@pytest.mark.parametrize(
    "change",
    [
        {"start_date": "2026-09-12"},
        {"end_date": date(2026, 9, 19)},
        {"end_date": date(2026, 9, 11)},
        {"poi_ids": ()},
        {"vehicle_ids": ()},
        {"vehicle_ids": ("3|4",)},
        {"driver_ids": ("5",)},
    ],
)
def test_reports_require_explicit_bounded_dates_and_entity_scope(change):
    calls = []
    client = StartrackClient(config(), httpx.MockTransport(lambda request: calls.append(request)))
    try:
        with pytest.raises(StartrackReadError):
            client.list_visits(
                **(
                    {
                        "start_date": date(2026, 9, 12),
                        "end_date": date(2026, 9, 12),
                        "poi_ids": ("2",),
                        "vehicle_ids": ("3",),
                    }
                    | change
                )
            )
    finally:
        client.close()
    assert calls == []


def test_report_rate_limit_is_bounded_without_sleep_or_retry(monkeypatch):
    now = [0.0]
    monkeypatch.setattr("app.integrations.startrack.monotonic", lambda: now[0])
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"success": True, "responses": []})

    client = StartrackClient(config(), httpx.MockTransport(handler))
    kwargs = {"form_id": "1", "start_date": date(2026, 9, 12), "end_date": date(2026, 9, 12)}
    try:
        for _ in range(10):
            client.list_form_responses(**kwargs)
        with pytest.raises(StartrackReadError, match="límite local"):
            client.list_form_responses(**kwargs)
        assert len(calls) == 10
        now[0] = 301
        client.list_form_responses(**kwargs)
        assert len(calls) == 11
    finally:
        client.close()


def test_unpaged_report_record_overflow_is_visible():
    client = StartrackClient(
        config(max_report_records=1),
        httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "success": True,
                    "responses": [
                        {"id": 1, "date": 1789224000},
                        {"id": 2, "date": 1789224001},
                    ],
                },
            )
        ),
    )
    try:
        with pytest.raises(StartrackReadError, match="límite de registros"):
            client.list_form_responses(
                form_id="1", start_date=date(2026, 9, 12), end_date=date(2026, 9, 12)
            )
    finally:
        client.close()
