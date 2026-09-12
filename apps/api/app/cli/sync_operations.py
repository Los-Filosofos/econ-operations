"""Run explicitly enabled integration cycles; no schema changes or implicit retries."""

import argparse
from threading import Event

from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.nexus import NexusConnector
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.services.workflow import WorkflowError, WorkflowService


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincronizar operaciones de ECON")
    parser.add_argument("--mode", choices=("fixture", "live"), default="live")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=120)
    args = parser.parse_args()
    if not 60 <= args.interval <= 3600:
        parser.error("El intervalo debe estar entre 60 y 3600 segundos.")
    settings = Settings()
    engine = build_engine(settings.database_url)
    nexus = NexusConnector(settings)
    startrack = StartrackClient(
        StartrackReadConfig(
            enabled=settings.allow_live_reads,
            allow_writes=settings.allow_live_writes,
            api_key=settings.startrack_api_key,
            password=settings.startrack_password,
            page_size=settings.startrack_page_size,
            max_pages=settings.startrack_max_pages,
            timeout_seconds=settings.startrack_timeout_seconds,
            budget_seconds=settings.startrack_budget_seconds,
        )
    )
    service = WorkflowService(settings, engine, nexus, startrack)
    stop = Event()
    try:
        while True:
            try:
                result = service.run_cycle(args.mode)
                print(result.message, flush=True)
                print(f"Movimientos consultados: {len(result.movements)}", flush=True)
            except WorkflowError as error:
                print(str(error), flush=True)
                if not args.watch:
                    return 1
            if not args.watch:
                return 0
            stop.wait(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        nexus.close()
        startrack.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
