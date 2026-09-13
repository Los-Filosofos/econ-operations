"""Validated URL state. Browser state never grants access to a provider."""

from dataclasses import dataclass
from urllib.parse import parse_qs, quote, urlencode

from app.models.hub import DataMode

FILTERS = {
    "all",
    "pending_started",
    "approved_unassigned",
    "unassigned",
    "active_failures",
    "unlinked",
}


@dataclass(frozen=True)
class QueryContext:
    mode: DataMode = "fixture"
    query: str = ""
    filter: str = "all"

    @property
    def read_key(self) -> list[str]:
        return [self.mode, self.query]

    def href(self, path: str = "/", *, filter: str = "all") -> str:
        params = {"mode": self.mode}
        if self.query:
            params["q"] = self.query
        if filter != "all":
            params["filter"] = filter
        return f"{path}?{urlencode(params)}"

    def equipment_href(self, identifier: str) -> str:
        return self.href(f"/maquinaria/{quote(identifier, safe='')}", filter=self.filter)

    def request_href(self, identifier: str) -> str:
        return self.href(f"/solicitudes/{quote(identifier, safe='')}", filter=self.filter)

    def movement_href(self, identifier: str) -> str:
        return self.href(f"/operaciones/{quote(identifier, safe='')}", filter=self.filter)

    def for_read(self, path: str | None) -> "QueryContext":
        # Search limits lists, never the record opened from one of their links.
        normalized = (path or "/").rstrip("/") or "/"
        if normalized.startswith(("/maquinaria/", "/solicitudes/")):
            return QueryContext(mode=self.mode)
        return self


def parse_context(search: str | None) -> QueryContext:
    try:
        params = parse_qs((search or "").lstrip("?"), keep_blank_values=True, max_num_fields=10)
    except ValueError as error:
        raise ValueError("La dirección contiene demasiados parámetros.") from error
    if any(len(value) != 1 for value in params.values()):
        raise ValueError("La dirección contiene parámetros repetidos.")
    mode = params.get("mode", ["fixture"])[0]
    query = params.get("q", [""])[0].strip()
    selected_filter = params.get("filter", ["all"])[0]
    if mode not in {"fixture", "live"}:
        raise ValueError("El origen debe ser muestras proporcionadas o sandbox actual sintético.")
    if len(query) > 100:
        raise ValueError("La búsqueda admite hasta 100 caracteres.")
    if selected_filter not in FILTERS:
        raise ValueError("El filtro de la dirección no es válido.")
    return QueryContext(mode=mode, query=query, filter=selected_filter)
