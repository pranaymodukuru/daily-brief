"""Puzzles generated in code, where the agent can't be trusted to be correct.

A sudoku is seeded by its date, so yesterday's solution can be printed today
without storing anything.
"""

import random
from datetime import date

# Clues left on the board; fewer clues is harder.
LEVELS = {"easy": 38, "medium": 32, "hard": 27}


def _candidates(g: list[int], i: int) -> set[int]:
    r, c = divmod(i, 9)
    br, bc = r - r % 3, c - c % 3
    used = {g[r * 9 + k] for k in range(9)} | {g[k * 9 + c] for k in range(9)}
    used |= {g[(br + a) * 9 + bc + b] for a in range(3) for b in range(3)}
    return set(range(1, 10)) - used


def _solve(g: list[int], rng: random.Random | None = None, limit: int = 1) -> int:
    """Fill g in place with the first solution; return how many exist (up to limit)."""
    empty = [i for i, v in enumerate(g) if not v]
    if not empty:
        return 1
    i = min(empty, key=lambda i: len(_candidates(g, i)))
    opts = list(_candidates(g, i))
    if rng:
        rng.shuffle(opts)
    found = 0
    for v in opts:
        g[i] = v
        found += _solve(g, rng, limit - found)
        if found >= limit:
            if limit == 1:
                return found  # keep the filled grid
            break
    g[i] = 0
    return found


def sudoku(day: date, level: str = "easy") -> tuple[list[int], list[int]]:
    """Return (puzzle, solution) as 81 ints, 0 for blanks. Unique solution."""
    rng = random.Random(f"sudoku-{day.isoformat()}-{level}")
    solution = [0] * 81
    _solve(solution, rng)
    puzzle = solution[:]
    clues = 81
    for i in rng.sample(range(81), 81):
        if clues <= LEVELS.get(level, LEVELS["easy"]):
            break
        keep, puzzle[i] = puzzle[i], 0
        if _solve(puzzle[:], limit=2) != 1:
            puzzle[i] = keep
        else:
            clues -= 1
    return puzzle, solution
