"""Run explicitly enabled integration cycles; no schema changes or implicit retries."""

import argparse
from time import sleep

from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.nexus import NexusConnector
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.services.workflow import SyncInProgress, WorkflowError, WorkflowService


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
    startrack = StartrackClient(StartrackReadConfig.from_settings(settings))
    service = WorkflowService(settings, engine, nexus, startrack)
    try:
        while True:
            try:
                result = service.run_cycle(args.mode)
                print(result.message, flush=True)
                print(f"Movimientos consultados: {len(result.movements)}", flush=True)
            except SyncInProgress as error:
                # Another process (or thread) owns the cycle lock: nothing ran here and
                # nothing is retried early; a watch simply waits for the next interval.
                print(f"Ciclo omitido: {error}", flush=True)
                if not args.watch:
                    return 1
            except WorkflowError as error:
                print(str(error), flush=True)
                if not args.watch:
                    return 1
            if not args.watch:
                return 0
            sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        nexus.close()
        startrack.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
