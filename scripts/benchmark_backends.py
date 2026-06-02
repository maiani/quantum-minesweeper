#!/usr/bin/env python
"""Benchmark stabilizer backends on the operations that dominate gameplay cost.

Run:  python scripts/benchmark_backends.py [--backends stim,purepy,qiskit]

The per-render hot path is the whole-board observables (expected_mines +
entanglement_score), evaluated on every /game render. This script times that,
plus board construction and a flood-fill measurement, across representative
board sizes, and reports each backend relative to Stim.
"""

from __future__ import annotations

import argparse
from time import perf_counter

import numpy as np

from qminesweeper.board import QMineSweeperBoard

BACKENDS = {
    "stim": "qminesweeper.stim_backend:StimBackend",
    "purepy": "qminesweeper.purepy_backend:PurePyBackend",
    "qiskit": "qminesweeper.qiskit_backend:QiskitBackend",
}

# (rows, cols) — the largest is the 25x15 setup preset (375 qubits).
SIZES = [(8, 8), (10, 10), (15, 15), (25, 15)]


def _load(path: str):
    mod, cls = path.split(":")
    import importlib

    return getattr(importlib.import_module(mod), cls)


def _build(backend_cls, rows, cols, mines, ent_level, seed):
    np.random.seed(seed)
    b = QMineSweeperBoard(rows, cols, backend=backend_cls(), flood_fill=True)
    if ent_level == 0:
        b.span_classical_mines(mines)
    else:
        b.span_random_stabilizer_mines(mines, level=ent_level)
    b.set_clue_basis("Z")
    return b


def _time(fn, repeat=1):
    best = float("inf")
    for _ in range(repeat):
        t0 = perf_counter()
        fn()
        best = min(best, perf_counter() - t0)
    return best


def bench(backend_cls, rows, cols):
    n = rows * cols
    mines = max(1, n // 20)
    # construction (classical mines)
    t_build = _time(lambda: _build(backend_cls, rows, cols, mines, 0, seed=1))
    # per-render observables on a built board (the hot path), best of 3
    board = _build(backend_cls, rows, cols, mines, 0, seed=1)
    t_render = _time(lambda: (board.expected_mines(), board.entanglement_score("mean")), repeat=3)
    # a flood-fill measurement from a corner on a fresh board (build + flood)
    t_flood = _time(lambda: _build(backend_cls, rows, cols, mines, 0, seed=2).measure_cell(0, 0))
    return {"build": t_build, "render": t_render, "flood": t_flood}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", default="stim,purepy")
    args = ap.parse_args()
    names = [b.strip() for b in args.backends.split(",") if b.strip()]
    classes = {name: _load(BACKENDS[name]) for name in names}

    print(f"{'board':>8} {'qubits':>7} {'metric':>8} " + " ".join(f"{name:>12}" for name in names) + "   (vs stim)")
    print("-" * (28 + 13 * len(names) + 12))
    for rows, cols in SIZES:
        results = {name: bench(cls, rows, cols) for name, cls in classes.items()}
        for metric in ("build", "render", "flood"):
            cells = [f"{results[name][metric] * 1e3:>10.2f}ms" for name in names]
            ratio = ""
            if "stim" in names and results["stim"][metric] > 0:
                worst = max(results[name][metric] for name in names)
                ratio = f"   {worst / results['stim'][metric]:>5.0f}x"
            tag = f"{rows}x{cols}" if metric == "build" else ""
            q = f"{rows * cols}" if metric == "build" else ""
            print(f"{tag:>8} {q:>7} {metric:>8} " + " ".join(cells) + ratio)
        print()


if __name__ == "__main__":
    main()
