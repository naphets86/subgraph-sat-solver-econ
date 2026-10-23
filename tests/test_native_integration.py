"""Integration checks against the compiled C++ solver and subgraph artifacts."""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _build_dir(variable: str, sibling: str) -> Path:
    configured = os.environ.get(variable)
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / sibling / "build"


def _executable(build_dir: Path, *stems: str) -> Path:
    for stem in stems:
        for suffix in (".exe", ""):
            candidate = build_dir / f"{stem}{suffix}"
            if candidate.is_file():
                return candidate
    pytest.skip(f"C++-Build-Artefakt {stems} fehlt in {build_dir}")


def test_subgraph_sat_solver_cpp_test_suite():
    build_dir = _build_dir("SUBGRAPH_SAT_SOLVER_BUILD_DIR", "subgraph-sat-solver")
    executable = _executable(build_dir, "sat-tests")
    result = subprocess.run(
        [str(executable)],
        capture_output=True,
        timeout=120,
        check=False,
    )
    output = result.stdout.decode("utf-8", errors="replace")
    error = result.stderr.decode("utf-8", errors="replace")
    assert result.returncode == 0, output + error
    assert "Failed:         0" in output


def test_csubgraph_cpp_test_suite():
    build_dir = _build_dir("CSUBGRAPH_BUILD_DIR", "csubgraph")
    executable = _executable(build_dir, "subgraph-tests")
    result = subprocess.run(
        [str(executable)],
        capture_output=True,
        timeout=120,
        check=False,
    )
    output = result.stdout.decode("utf-8", errors="replace")
    error = result.stderr.decode("utf-8", errors="replace")
    assert result.returncode == 0, output + error
    assert "[  PASSED  ]" in output


def test_csubgraph_cpp_cli_decides_subgraph_instances():
    build_dir = _build_dir("CSUBGRAPH_BUILD_DIR", "csubgraph")
    executable = _executable(build_dir, "subgraph", "subgraph-cli")

    def run_cli(graph_a, graph_b):
        payload = json.dumps({"graph_a": graph_a, "graph_b": graph_b})
        result = subprocess.run(
            [str(executable)],
            input=payload.encode("utf-8"),
            capture_output=True,
            timeout=30,
            check=False,
        )
        output = result.stdout.decode("utf-8", errors="replace")
        error = result.stderr.decode("utf-8", errors="replace")
        assert result.returncode == 0, output + error
        return json.loads(output)

    # Dreiecksgraph (3 Knoten mit Kanten 0-1, 1-2, 2-0)
    cycle3 = [
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
    ]

    # Graph mit 2 isolierten Knoten ohne Kanten (keine Subgraph-Beziehung zu cycle3)
    empty2 = [
        [0, 0],
        [0, 0],
    ]

    # 1. Identischer Graph-Vergleich
    identical_res = run_cli(cycle3, cycle3)
    assert identical_res["result"] == "IDENTICAL"
    assert identical_res["result_code"] == 3

    # 2. Keine Subgraph-Beziehung
    both_res = run_cli(cycle3, empty2)
    assert both_res["result"] == "KEEP_BOTH"
    assert both_res["result_code"] == 2