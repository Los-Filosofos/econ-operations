"""Login page, header identity, role gating and user administration through real Dash callbacks."""

import json
import re
from contextlib import contextmanager

import pytest
from plotly.utils import PlotlyJSONEncoder

from app.core.auth import Role
from app.dashboard.auth_views import DENIED, safe_next
from app.models.workflow import WorkflowOverview
from tests.test_auth import add_user, build_app, login, open_client

ROUTE = [("root", "children"), ("view", "data")]
RENDER = [
    ("content", "children"),
    ("navigation", "children"),
    ("mobile-navigation-links", "children"),
    ("scope", "children"),
]
ADMIN_SAVE = [
    ("admin-result", "data"),
    ("user-modal", "opened"),
    ("new-name", "value"),
    ("new-email", "value"),
    ("new-password", "value"),
]


@pytest.fixture
def app(tmp_path):
    return build_app(tmp_path)


@contextmanager
def open_ready(app):
    """Dash finalizes its callbacks when it first serves the layout, before any callback."""
    with open_client(app) as client:
        assert client.get("/_dash-layout").status_code == 200
        yield client


def callback(client, outputs, inputs, state=(), changed=None):
    targets = [{"id": identifier, "property": prop} for identifier, prop in outputs]
    names = [f"{identifier}.{prop}" for identifier, prop in outputs]
    wanted = names[0] if len(names) == 1 else ".." + "...".join(names) + ".."
    # Outputs declared with allow_duplicate carry a hash suffix in the registered key.
    registered = client.app.state.dashboard.callback_map
    payload = {
        "output": next((key for key in registered if re.sub(r"@\w+", "", key) == wanted), wanted),
        "outputs": targets[0] if len(targets) == 1 else targets,
        "inputs": [
            {"id": identifier, "property": prop, "value": value}
            for identifier, prop, value in inputs
        ],
        "state": [
            {"id": identifier, "property": prop, "value": value}
            for identifier, prop, value in state
        ],
        "changedPropIds": [changed] if changed else [],
    }
    response = client.post("/_dash-update-component", json=payload)
    assert response.status_code in {200, 204}, response.text
    return response.json()["response"] if response.status_code == 200 else {}


def route(client, path, search="", view=None):
    return callback(
        client,
        ROUTE,
        [("url", "pathname", path)],
        [("url", "search", search), ("view", "data", view)],
        "url.pathname",
    )


def render(client, path, search="?mode=fixture", snapshot=None, workflow=None, changed=None):
    return callback(
        client,
        RENDER,
        [
            ("url", "pathname", path),
            ("url", "search", search),
            ("snapshot", "data", snapshot),
            ("workflow-snapshot", "data", workflow),
        ],
        changed=changed,
    )


def snapshot(client, path="/", search="?mode=fixture"):
    return callback(
        client,
        [("snapshot", "data")],
        [
            ("url", "search", search),
            ("refresh", "n_clicks", 0),
            ("url", "pathname", path),
            ("workflow-action-result", "data", None),
        ],
        [("snapshot", "data", None)],
        "url.search",
    )


def workflow_snapshot(client, search="?mode=fixture"):
    return callback(
        client,
        [("workflow-snapshot", "data")],
        [
            ("url", "search", search),
            ("refresh", "n_clicks", 0),
            ("workflow-action-result", "data", None),
        ],
        changed="url.search",
    )


def rendered(client, path, search="?mode=fixture"):
    hub = snapshot(client, path, search)["snapshot"]["data"]
    workflow = workflow_snapshot(client, search)["workflow-snapshot"]["data"]
    return render(client, path, search, hub, workflow)


def text(component) -> str:
    return json.dumps(component, cls=PlotlyJSONEncoder, ensure_ascii=False)


def save(client, *, create=0, edit=0, new=None, user_id=None, edited=None):
    new = new or {}
    edited = edited or {}
    return callback(
        client,
        ADMIN_SAVE,
        [("user-create", "n_clicks", create), ("user-save", "n_clicks", edit)],
        [
            ("new-name", "value", new.get("name")),
            ("new-email", "value", new.get("email")),
            ("new-role", "value", new.get("role", "lectura")),
            ("new-password", "value", new.get("password")),
            ("user-edit-id", "data", user_id),
            ("user-name", "value", edited.get("name")),
            ("user-role", "value", edited.get("role")),
            ("user-active", "checked", edited.get("active", True)),
            ("user-password", "value", edited.get("password")),
        ],
        "user-create.n_clicks" if create else "user-save.n_clicks",
    )["admin-result"]["data"]


def users_view(client):
    outputs = [("admin-users", "children"), ("admin-feedback", "children")]
    return callback(client, outputs, [("admin-result", "data", None)])


@pytest.mark.parametrize(
    "search, expected",
    [
        ("?next=%2Fsolicitudes%3Fmode%3Dfixture", "/solicitudes?mode=fixture"),
        ("?next=https%3A%2F%2Fevil.example%2F", "/"),
        ("?next=%2F%2Fevil.example", "/"),
        ("?next=%2F%5Cevil.example", "/"),
        ("", "/"),
        (None, "/"),
    ],
)
def test_next_only_accepts_internal_relative_paths(search, expected):
    assert safe_next(search) == expected


def test_login_page_renders_without_session_and_root_redirects(app):
    with open_ready(app) as client:
        assert client.get("/login").status_code == 200
        home = client.get("/", follow_redirects=False)
        assert home.status_code == 302 and home.headers["location"] == "/login?next=%2F"
        page = route(client, "/login", "?next=https%3A%2F%2Fevil.example%2F")
        assert page["view"]["data"] == "login"
        serialized = text(page["root"]["children"])
        assert "login-email" in serialized and "login-password" in serialized
        assert "Iniciar sesión" in serialized and "evil.example" not in serialized
        # Anonymous application routes render a redirect to the login page, never the shell.
        redirect = route(client, "/solicitudes", "?mode=fixture")
        assert redirect["view"]["data"] == "redirect"
        assert redirect["root"]["children"]["props"]["href"] == (
            "/login?next=%2Fsolicitudes%3Fmode%3Dfixture"
        )


def test_callbacks_without_session_expose_no_data(app):
    with open_ready(app) as client:
        assert snapshot(client) == {}
        assert workflow_snapshot(client) == {}
        page = render(client, "/", "?mode=fixture")
        serialized = text(page)
        assert page["content"]["children"]["props"]["href"] == "/login?next=%2F%3Fmode%3Dfixture"
        assert "equipment" not in serialized and "requests" not in serialized


def test_signed_in_user_gets_the_shell_with_identity_and_login_redirects_home(app):
    with open_ready(app) as client:
        add_user(app, "ana@example.com", Role.lectura)
        login(client, "ana@example.com")
        shell = route(client, "/", "?mode=fixture")
        assert shell["view"]["data"] == "app"
        serialized = text(shell["root"]["children"])
        assert "ana" in serialized and "Lectura" in serialized and "Cerrar sesión" in serialized
        assert route(client, "/", "?mode=fixture", view="app") == {}
        assert route(client, "/login")["root"]["children"]["props"]["href"] == "/"
        page = rendered(client, "/")
        assert "operations-graph-world" in text(page["content"]["children"])
        assert page["scope"]["children"] is None


def test_read_role_sees_no_action_forms_and_no_administration(app):
    with open_ready(app) as client:
        add_user(app, "lectura@example.com", Role.lectura)
        login(client, "lectura@example.com")
        hub = snapshot(client)["snapshot"]["data"]["hub"]
        request = next(item for item in hub["requests"] if item["machinery_id"])
        detail = rendered(client, f"/solicitudes/{request['id']}")
        serialized = text(detail["content"]["children"])
        assert DENIED in serialized
        assert "workflow-field" not in serialized and "workflow-action" not in serialized
        operations = text(rendered(client, "/operaciones")["content"]["children"])
        assert DENIED in operations and "workflow-action" not in operations
        assert "/administracion" not in text(detail["navigation"]["children"])
        admin = text(render(client, "/administracion")["content"]["children"])
        assert "Sin acceso" in admin and "admin-users" not in admin
        assert "Sin acceso" in text(users_view(client)["admin-users"]["children"])
        assert save(client, create=1, new={"email": "x@example.com"})["ok"] is False


def test_logistics_role_keeps_transfer_forms(app):
    with open_ready(app) as client:
        add_user(app, "ops@example.com", Role.logistica)
        login(client, "ops@example.com")
        hub = snapshot(client)["snapshot"]["data"]["hub"]
        request = next(item for item in hub["requests"] if item["machinery_id"])
        serialized = text(rendered(client, f"/solicitudes/{request['id']}")["content"]["children"])
        assert DENIED not in serialized and "workflow-field" in serialized


def test_admin_manages_users_from_the_dashboard(app):
    with open_ready(app) as client:
        admin = add_user(app, "admin@example.com", Role.admin)
        login(client, "admin@example.com")
        page = render(client, "/administracion")
        assert "/administracion" in text(page["navigation"]["children"])
        assert "admin-users" in text(page["content"]["children"])
        listed = text(users_view(client)["admin-users"]["children"])
        assert "admin@example.com" in listed and "Administrador" in listed

        new = {"name": "Nueva", "email": "Nueva@example.com", "role": "logistica"}
        weak = save(client, create=1, new={**new, "password": "short"})
        assert weak["ok"] is False and "12 caracteres" in weak["message"]
        created = save(client, create=1, new={**new, "password": "another-long-secret"})
        assert created["ok"] is True, created
        duplicate = save(client, create=1, new={**new, "password": "another-long-secret"})
        assert duplicate == {"ok": False, "message": "El email ya existe."}
        listed = text(users_view(client)["admin-users"]["children"])
        assert "nueva@example.com" in listed and "Logística y Equipo" in listed

        new_id = next(
            user["id"]
            for user in client.get("/api/v1/users").json()
            if user["email"].startswith("nueva")
        )
        edited = {"name": "Nueva", "role": "lectura", "active": False}
        assert save(client, edit=1, user_id=new_id, edited=edited)["ok"] is True
        record = client.get("/api/v1/users").json()
        changed = next(user for user in record if user["id"] == new_id)
        assert changed["role"] == "lectura" and changed["is_active"] is False

        own = {"name": "admin", "role": "admin", "active": False}
        assert save(client, edit=1, user_id=admin.id, edited=own)["message"] == (
            "No puedes desactivar tu propia cuenta."
        )
        demoted = {"name": "admin", "role": "lectura", "active": True}
        assert save(client, edit=1, user_id=admin.id, edited=demoted)["message"] == (
            "Debe quedar al menos un administrador activo."
        )
        assert client.get("/api/v1/auth/me").json()["role"] == "admin"


def test_without_auth_required_the_header_names_the_local_session(tmp_path):
    app = build_app(tmp_path, auth_required=False, session_secret=None)
    with open_ready(app) as client:
        shell = text(route(client, "/")["root"]["children"])
        assert "Sesión local sin autenticación" in shell
        assert "/administracion" not in text(render(client, "/")["navigation"]["children"])
        # There is no login to show: /login goes home instead of offering a useless form.
        assert route(client, "/login")["root"]["children"]["props"]["href"] == "/"


def test_reception_form_follows_declare_reception_permission(app):
    """A sent live movement offers the receipt form to gerencia_proyecto and logistica only."""
    from tests.test_workflow_ui import action, fields

    with open_ready(app) as client:
        for role in (Role.logistica, Role.gerencia_proyecto, Role.lectura):
            add_user(app, f"{role.value}@example.com", role)
        login(client, "logistica@example.com")
        assert action(client, "save", fields())["ok"]
        overview = WorkflowOverview.model_validate(
            workflow_snapshot(client)["workflow-snapshot"]["data"]["overview"]
        )
        sent = overview.movements[0].model_copy(
            update={"mode": "live", "state": "sent", "job_id": "test-job"}
        )
        live = WorkflowOverview(
            available=True, message="Registro de prueba", management_enabled=True, movements=[sent]
        )
        snapshot = {"mode": "live", "overview": live.model_dump(mode="json")}
        path = f"/operaciones/{sent.id}"
        expected = {Role.logistica: True, Role.gerencia_proyecto: True, Role.lectura: False}
        for role, can_declare in expected.items():
            login(client, f"{role.value}@example.com")
            page = render(client, path, "?mode=live", None, snapshot)
            serialized = text(page["content"]["children"])
            assert ('"field": "receiver"' in serialized) is can_declare, role
            assert ('"action": "receipt"' in serialized) is can_declare, role
            if role is Role.lectura:
                assert DENIED in serialized
