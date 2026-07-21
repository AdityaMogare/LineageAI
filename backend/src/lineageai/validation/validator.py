import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

from lineageai.models import GeneratedModel, MetadataContext, ValidationResult
from lineageai.validation.error_parser import parse_dbt_errors
from lineageai.validation.stubs import StubDatabaseBuilder


class DbtValidator:
    def __init__(self, stub_builder: StubDatabaseBuilder | None = None) -> None:
        self.stub_builder = stub_builder or StubDatabaseBuilder()

    def validate(self, model: GeneratedModel, context: MetadataContext) -> ValidationResult:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="lineageai-dbt-") as temp:
            root = Path(temp)
            database_path = root / "validation.duckdb"
            self.stub_builder.build(context, database_path)
            self._write_project(root, database_path, model)

            combined_stdout: list[str] = []
            combined_stderr: list[str] = []
            for operation in ("parse", "build"):
                command = [
                    self._dbt_executable(),
                    operation,
                    "--project-dir",
                    str(root),
                    "--profiles-dir",
                    str(root),
                    "--no-use-colors",
                ]
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                combined_stdout.append(completed.stdout)
                combined_stderr.append(completed.stderr)
                if completed.returncode:
                    output = "\n".join((*combined_stdout, *combined_stderr))
                    return ValidationResult(
                        success=False,
                        command=f"dbt {operation}",
                        stdout="\n".join(combined_stdout),
                        stderr="\n".join(combined_stderr),
                        diagnostics=parse_dbt_errors(output),
                        elapsed_seconds=time.monotonic() - started,
                    )

            return ValidationResult(
                success=True,
                command="dbt build",
                stdout="\n".join(combined_stdout),
                stderr="\n".join(combined_stderr),
                elapsed_seconds=time.monotonic() - started,
            )

    @staticmethod
    def _dbt_executable() -> str:
        sibling = Path(sys.executable).with_name("dbt")
        executable = shutil.which("dbt") or (str(sibling) if sibling.exists() else None)
        if executable is None:
            raise RuntimeError("dbt executable not found; install project dependencies")
        return executable

    @staticmethod
    def _write_project(root: Path, database_path: Path, model: GeneratedModel) -> None:
        models = root / "models"
        models.mkdir()
        (root / "dbt_project.yml").write_text(
            yaml.safe_dump(
                {
                    "name": "lineageai_validation",
                    "version": "1.0.0",
                    "config-version": 2,
                    "profile": "lineageai_validation",
                    "model-paths": ["models"],
                    "target-path": "target",
                    "clean-targets": ["target"],
                },
                sort_keys=False,
            )
        )
        (root / "profiles.yml").write_text(
            yaml.safe_dump(
                {
                    "lineageai_validation": {
                        "target": "validation",
                        "outputs": {
                            "validation": {
                                "type": "duckdb",
                                "path": str(database_path),
                                "schema": "main",
                                "threads": 1,
                            }
                        },
                    }
                },
                sort_keys=False,
            )
        )
        (models / f"{model.name}.sql").write_text(model.sql + "\n")
        (models / "schema.yml").write_text(model.schema_yml.rstrip() + "\n")
