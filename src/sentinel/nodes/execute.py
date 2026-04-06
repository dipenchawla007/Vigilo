from __future__ import annotations

import logging
from pathlib import Path
import shutil
import subprocess
import sys

from sentinel.nodes.common import add_progress, now_iso
from sentinel.state import ExecutionArtifact, ExecutionResult, InvestigationState

logger = logging.getLogger(__name__)

DOCKER_IMAGE = "sentinel-sandbox"
EXECUTION_TIMEOUT = 120


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _image_exists(image: str) -> bool:
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _build_image() -> bool:
    sandbox_dir = Path(__file__).resolve().parents[3] / "sandbox"
    if not (sandbox_dir / "Dockerfile").exists():
        return False
    try:
        result = subprocess.run(
            ["docker", "build", "-t", DOCKER_IMAGE, "."],
            cwd=str(sandbox_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_in_docker(script_path: Path, workspace: Path) -> tuple[bool, str, str, int]:
    """Execute the script inside a Docker container with network restrictions."""
    if not _image_exists(DOCKER_IMAGE):
        if not _build_image():
            raise RuntimeError("Failed to build sandbox Docker image")

    cmd = [
        "docker", "run",
        "--rm",
        "--network", "bridge",
        "--memory", "512m",
        "--cpus", "1.0",
        "-v", f"{workspace}:/workspace",
        "-v", f"{script_path}:/workspace/script.py:ro",
        "-w", "/workspace",
        DOCKER_IMAGE,
        "python", "/workspace/script.py",
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
        )
        return (
            completed.returncode == 0,
            completed.stdout,
            completed.stderr,
            completed.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        return False, exc.stdout or "", (exc.stderr or "") + "\nDocker execution timed out.", 1


def _run_in_subprocess(script_path: Path, workspace: Path) -> tuple[bool, str, str, int]:
    """Execute via the in-process sandbox runner (fallback when Docker is unavailable)."""
    runner_path = Path(__file__).resolve().parents[3] / "sandbox" / "runner.py"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(runner_path),
                "--script", str(script_path),
                "--workspace", str(workspace),
                "--allow-host", "api.fda.gov",
            ],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
        )
        return (
            completed.returncode == 0,
            completed.stdout,
            completed.stderr,
            completed.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        return False, exc.stdout or "", (exc.stderr or "") + "\nExecution timed out.", 1


def _collect_artifacts(workspace: Path) -> list[ExecutionArtifact]:
    artifacts: list[ExecutionArtifact] = []
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            suffix = path.suffix.lower()
            kind = "text"
            if suffix == ".py":
                kind = "script"
            elif suffix == ".png":
                kind = "plot"
            elif suffix == ".json":
                kind = "json"
            artifacts.append(ExecutionArtifact(filename=path.name, kind=kind, path=str(path)))
    return artifacts


def run(state: InvestigationState, workspace: Path) -> InvestigationState:
    add_progress(state, "execute", "started", "Executing generated analysis code.")
    workspace.mkdir(parents=True, exist_ok=True)
    script_path = workspace / "generated_investigation.py"
    script_path.write_text(state["generated_code"])

    use_docker = _docker_available()
    if use_docker:
        logger.info("Docker available — running in container sandbox")
        add_progress(state, "execute", "started", "Running in Docker sandbox.")
        success, stdout, stderr, exit_code = _run_in_docker(script_path, workspace)
    else:
        logger.info("Docker not available — falling back to subprocess sandbox")
        success, stdout, stderr, exit_code = _run_in_subprocess(script_path, workspace)

    artifacts = _collect_artifacts(workspace)
    state["execution"] = ExecutionResult(
        success=success,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        artifacts=artifacts,
        generated_at=now_iso(),
    )
    add_progress(
        state,
        "execute",
        "completed" if success else "failed",
        f"Execution {'succeeded' if success else 'failed'} (exit code {exit_code})."
        + (f" {len(artifacts)} artifact(s) collected." if success else ""),
    )
    return state
