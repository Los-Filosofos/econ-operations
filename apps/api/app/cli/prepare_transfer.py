"""Print a transfer review from supplied local samples without accessing providers."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.integrations.fixtures import fixture_records
from app.services.transfers import TransferMapping, prepare_transfer

MAX_MAPPING_BYTES = 64_000


def _error(message: str) -> int:
    print(
        json.dumps({"error": message, "remote_writes": False}, ensure_ascii=False), file=sys.stderr
    )
    return 2


def _read_mapping(path: Path) -> TransferMapping:
    # A mapping is a small local data file, never a URL or a network-share location.
    if str(path).startswith(("\\\\", "//")):
        raise ValueError("Se requiere un archivo local.")
    with path.open("rb") as handle:
        content = handle.read(MAX_MAPPING_BYTES + 1)
    if len(content) > MAX_MAPPING_BYTES:
        raise ValueError("El archivo excede el tamaño permitido.")
    return TransferMapping.model_validate_json(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepara un traslado desde las muestras locales entregadas. "
            "No consulta ni modifica Prisma o Startrack."
        )
    )
    parser.add_argument(
        "--request-source-id", required=True, help="UUID exacto de la solicitud Prisma"
    )
    parser.add_argument(
        "--mapping", type=Path, help="Archivo JSON local con correspondencias explícitas"
    )
    arguments = parser.parse_args(argv)

    try:
        equipment, requests = fixture_records()
    except (OSError, ValueError, KeyError, TypeError):
        return _error("No fue posible leer las muestras locales entregadas.")
    matching_requests = [
        request
        for request in requests
        if request.provenance.source_id == arguments.request_source_id
    ]
    if len(matching_requests) != 1:
        return _error("El ID debe identificar exactamente una solicitud en la muestra local.")
    request = matching_requests[0]
    matching_equipment = [item for item in equipment if item.id == request.machinery_id]
    if len(matching_equipment) > 1:
        return _error("La unidad asignada tiene registros ambiguos en la muestra local.")

    mapping = None
    if arguments.mapping is not None:
        try:
            mapping = _read_mapping(arguments.mapping)
        except (OSError, ValueError, ValidationError):
            return _error(
                "El mapeo debe ser un archivo JSON local válido con IDs y fecha explícitos."
            )
    result = prepare_transfer(
        request, matching_equipment[0] if matching_equipment else None, mapping
    )
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    # Keep Spanish and exported JSON intact when stdout is piped on Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
