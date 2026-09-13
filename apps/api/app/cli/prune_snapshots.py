"""Delete old hub cuts explicitly; events and movements are never pruned.

Process authority, like `sync_operations`: no user session is involved and nothing is
sent to any provider. The retention decision is the operator's, expressed as arguments
on every run; the application never prunes on its own (ADR 0006).
"""

import argparse
import sys

from app.core.config import Settings
from app.core.database import build_engine
from app.services.ledger import LedgerError, OperationsLedger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Poda cortes antiguos del hub (operation_snapshots) de un modo. Conserva siempre "
            "los más recientes; nunca toca operation_events ni operation_movements."
        )
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="live")
    parser.add_argument(
        "--keep-days",
        type=int,
        required=True,
        help="Conservar los cortes leídos o confirmados en los últimos N días (N ≥ 1).",
    )
    parser.add_argument(
        "--keep-latest",
        type=int,
        default=1,
        help="Conservar siempre los N cortes más recientes del modo (N ≥ 1; 1 por defecto).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Contar los cortes a eliminar sin borrarlos."
    )
    args = parser.parse_args(argv)
    if args.keep_days < 1:
        parser.error("--keep-days debe ser un entero mayor o igual que 1.")
    if args.keep_latest < 1:
        parser.error("--keep-latest debe ser un entero mayor o igual que 1.")
    engine = build_engine(Settings().database_url)
    try:
        count = OperationsLedger(engine).prune_snapshots(
            args.mode,
            keep_days=args.keep_days,
            keep_latest=args.keep_latest,
            dry_run=args.dry_run,
        )
    except LedgerError as error:
        print(str(error), file=sys.stderr)
        return 2
    finally:
        engine.dispose()
    label = "Cortes que se eliminarían" if args.dry_run else "Cortes eliminados"
    print(
        f"{label} ({args.mode}, más de {args.keep_days} días, conservando los "
        f"{args.keep_latest} más recientes): {count}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
