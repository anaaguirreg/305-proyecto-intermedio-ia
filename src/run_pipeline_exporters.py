"""
Cicatrices Invisibles — top-level orchestrator for the 3 exporters.
Runs in order A3: ModelExporter → MasterExporter → ForenseExporter.
Each exporter reads its own config and writes to data/dashboard/.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_pipeline(
    project_root: Path,
    skip_model: bool = False,
    skip_master: bool = False,
    skip_forense: bool = False,
) -> dict[str, float]:
    """
    Executes the 3 exporters in order A3.
    Returns a dict of exporter_name -> elapsed_seconds.
    Halts on first failure — does not attempt recovery or rollback.

    Constructor signatures (must not be changed):
      ModelExporter(config_path, output_dir)
      MasterExporter(config_path: str)
      ForenseExporter(config_path: Path)
    """
    from src.exporters.model_exporter import ModelExporter
    from src.exporters.master_exporter import MasterExporter
    from src.exporters.forense_exporter import ForenseExporter

    logger = logging.getLogger("pipeline")
    timings: dict[str, float] = {}

    dashboard_dir = project_root / "data" / "dashboard"

    steps: list[tuple[str, bool]] = [
        ("ModelExporter",   skip_model),
        ("MasterExporter",  skip_master),
        ("ForenseExporter", skip_forense),
    ]

    for name, skip in steps:
        if skip:
            logger.info("%s SKIPPED (--skip flag)", name)
            continue

        logger.info("%s START", name)
        t0 = time.perf_counter()
        try:
            if name == "ModelExporter":
                exporter = ModelExporter(
                    config_path=project_root / "config" / "master_exporter_config.json",
                    output_dir=dashboard_dir,
                )
                exporter.build()
            elif name == "MasterExporter":
                exporter = MasterExporter(
                    config_path=str(project_root / "config" / "master_exporter_config.json"),
                )
                exporter.build()
            elif name == "ForenseExporter":
                exporter = ForenseExporter(
                    config_path=project_root / "config" / "forense_exporter_config.json",
                )
                exporter.build()
        except Exception as exc:
            logger.error("%s FAILED: %s", name, exc)
            raise

        elapsed = time.perf_counter() - t0
        timings[name] = elapsed
        logger.info("%s OK (%.2fs)", name, elapsed)

    return timings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--skip-model",   action="store_true")
    parser.add_argument("--skip-master",  action="store_true")
    parser.add_argument("--skip-forense", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    _setup_logging(args.verbose)
    logger = logging.getLogger("pipeline")
    try:
        timings = run_pipeline(
            project_root=args.project_root,
            skip_model=args.skip_model,
            skip_master=args.skip_master,
            skip_forense=args.skip_forense,
        )
    except Exception:
        logger.error("Pipeline halted.")
        return 1

    total = sum(timings.values())
    logger.info("Pipeline OK — total %.2fs", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
