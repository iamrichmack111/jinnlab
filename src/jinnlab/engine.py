from __future__ import annotations

from dataclasses import dataclass
from random import Random
from statistics import mean
from typing import Mapping, Sequence

from .strategies import custom_strategy_classes, build_rule_strategy


@dataclass(frozen=True)
class MatchResult:
    player1: str
    player2: str
    score1: float
    score2: float
    winner: str
    cooperation1: float
    cooperation2: float


@dataclass(frozen=True)
class TournamentRow:
    rank: int
    strategy: str
    score: float


@dataclass(frozen=True)
class EvolutionSnapshot:
    generation: int
    populations: dict[str, int]


def _axl():
    import axelrod as axl
    return axl


def strategy_catalog(extra_designs: Sequence[Mapping] | None = None):
    """Build the strategy catalog, including live aliases for custom families.

    Every saved design is available by its versioned display name (for example
    ``Richmack v2``). The bare family name (``Richmack``) is also registered as
    an alias for the newest saved version, which makes the Designer -> Batch
    workflow immediate and convenient.
    """
    axl = _axl()
    classes = list(axl.strategies) + custom_strategy_classes()
    designs = [dict(d) for d in (extra_designs or [])]
    classes.extend(build_rule_strategy(d) for d in designs)

    latest_by_family = {}
    for design in designs:
        family = str(design.get("family_name", "")).strip()
        if not family:
            continue
        version = int(design.get("version", 0) or 0)
        if family not in latest_by_family or version > int(latest_by_family[family].get("version", 0) or 0):
            latest_by_family[family] = design
    for family, design in latest_by_family.items():
        alias_design = dict(design)
        alias_design["display_name"] = family
        classes.append(build_rule_strategy(alias_design))

    unique = {}
    for cls in classes:
        unique[getattr(cls, "name", cls.__name__)] = cls
    return dict(sorted(unique.items(), key=lambda x: x[0].lower()))


def strategy_info(name: str, catalog: Mapping[str, type] | None = None) -> dict[str, str]:
    catalog = catalog or strategy_catalog()
    cls = catalog[name]
    doc = (cls.__doc__ or "No description available.").strip()
    classifier = getattr(cls, "classifier", {}) or {}
    return {
        "name": name,
        "description": " ".join(doc.split()),
        "memory": str(classifier.get("memory_depth", "unknown")),
        "stochastic": str(classifier.get("stochastic", "unknown")),
        "long_run": str(classifier.get("long_run_time", "unknown")),
    }


def run_match(player1_name: str, player2_name: str, turns: int = 200,
              repetitions: int = 1, seed: int | None = None,
              catalog: Mapping[str, type] | None = None) -> MatchResult:
    axl = _axl()
    catalog = catalog or strategy_catalog()
    p1_cls, p2_cls = catalog[player1_name], catalog[player2_name]
    scores1, scores2, coop1, coop2 = [], [], [], []
    for i in range(repetitions):
        match = axl.Match((p1_cls(), p2_cls()), turns=turns,
                          seed=None if seed is None else seed + i)
        actions = match.play()
        s1, s2 = match.final_score()
        scores1.append(float(s1)); scores2.append(float(s2))
        coop1.append(sum(a == axl.Action.C for a, _ in actions) / max(1, len(actions)))
        coop2.append(sum(b == axl.Action.C for _, b in actions) / max(1, len(actions)))
    a, b = mean(scores1), mean(scores2)
    winner = "Draw" if abs(a - b) < 1e-12 else (player1_name if a > b else player2_name)
    return MatchResult(player1_name, player2_name, a, b, winner, mean(coop1), mean(coop2))


def run_moran(player1_name: str, player2_name: str, seed: int | None = None,
              catalog: Mapping[str, type] | None = None) -> tuple[str, int]:
    axl = _axl(); catalog = catalog or strategy_catalog()
    mp = axl.MoranProcess([catalog[player1_name](), catalog[player2_name]()], seed=seed)
    populations = mp.play()
    final = populations[-1]
    c1, c2 = final[player1_name], final[player2_name]
    winner = "Draw" if c1 == c2 else (player1_name if c1 > c2 else player2_name)
    return winner, len(populations) - 1


def run_tournament(names: Sequence[str], turns: int = 100, repetitions: int = 3,
                   seed: int | None = None, catalog: Mapping[str, type] | None = None) -> list[TournamentRow]:
    if len(names) < 2:
        raise ValueError("Select at least two strategies")
    catalog = catalog or strategy_catalog()
    totals = {name: 0.0 for name in names}
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if j <= i:
                continue
            result = run_match(a, b, turns=turns, repetitions=repetitions,
                               seed=None if seed is None else seed + i * 1000 + j * 10,
                               catalog=catalog)
            totals[a] += result.score1
            totals[b] += result.score2
    ranked = sorted(totals.items(), key=lambda x: (-x[1], x[0]))
    return [TournamentRow(rank=i + 1, strategy=name, score=score)
            for i, (name, score) in enumerate(ranked)]


def run_matrix(names: Sequence[str], turns: int = 100, repetitions: int = 3,
               seed: int | None = None, catalog: Mapping[str, type] | None = None) -> dict[str, dict[str, float]]:
    if len(names) < 2:
        raise ValueError("Matrix needs at least two strategies")
    catalog = catalog or strategy_catalog()
    matrix: dict[str, dict[str, float]] = {n: {} for n in names}
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            result = run_match(a, b, turns, repetitions,
                               None if seed is None else seed + i * 1000 + j,
                               catalog)
            matrix[a][b] = result.score1
    return matrix


def run_population_evolution(initial: Mapping[str, int], generations: int = 100,
                             turns: int = 60, repetitions: int = 1,
                             mutation_rate: float = 0.01, seed: int | None = None,
                             catalog: Mapping[str, type] | None = None,
                             snapshot_every: int = 10, progress_callback=None) -> list[EvolutionSnapshot]:
    """Finite-population evolutionary simulation using payoff-proportional reproduction.

    Each generation computes expected payoff for each present strategy against the
    current population, then samples the next generation with a small mutation chance.
    """
    catalog = catalog or strategy_catalog()
    counts = {k: int(v) for k, v in initial.items() if int(v) > 0}
    if len(counts) < 2:
        raise ValueError("Evolution needs at least two strategies with positive populations")
    total_pop = sum(counts.values())
    rng = Random(seed)
    names = list(counts)
    payoff_cache: dict[tuple[str, str], float] = {}

    def payoff(a: str, b: str, generation: int) -> float:
        key = (a, b)
        if key not in payoff_cache:
            r = run_match(a, b, turns, repetitions,
                          None if seed is None else seed + len(payoff_cache) * 17,
                          catalog)
            payoff_cache[key] = r.score1 / max(1, turns)
        return payoff_cache[key]

    snapshots = [EvolutionSnapshot(0, dict(counts))]
    if progress_callback:
        progress_callback(snapshots[-1])
    for gen in range(1, generations + 1):
        fitness: dict[str, float] = {}
        for a in names:
            if counts.get(a, 0) <= 0:
                fitness[a] = 0.0
                continue
            weighted = 0.0
            opponents = 0
            for b in names:
                n = counts.get(b, 0) - (1 if a == b else 0)
                if n > 0:
                    weighted += payoff(a, b, gen) * n
                    opponents += n
            fitness[a] = weighted / max(1, opponents)

        min_fit = min(fitness.values())
        weights = [max(0.0001, fitness[n] - min_fit + 0.05) * counts.get(n, 0) for n in names]
        next_counts = {n: 0 for n in names}
        for _ in range(total_pop):
            parent = rng.choices(names, weights=weights, k=1)[0]
            child = rng.choice(names) if rng.random() < mutation_rate else parent
            next_counts[child] += 1
        counts = next_counts
        if gen % max(1, snapshot_every) == 0 or gen == generations:
            snapshots.append(EvolutionSnapshot(gen, dict(counts)))
            if progress_callback:
                progress_callback(snapshots[-1])
    return snapshots


def interpret_match(result: MatchResult, turns: int) -> str:
    margin = abs(result.score1 - result.score2)
    per_turn = margin / max(1, turns)
    if result.winner == "Draw":
        outcome = "Neither strategy gained a scoring advantage in this configuration."
    elif per_turn < 0.1:
        outcome = f"{result.winner} won, but the advantage is small; increase repetitions before treating it as robust."
    else:
        outcome = f"{result.winner} produced the higher average payoff under these exact conditions."
    cavg = (result.cooperation1 + result.cooperation2) / 2
    if cavg >= 0.75:
        coop = "The interaction was highly cooperative, suggesting the pair sustained mutual cooperation most of the time."
    elif cavg <= 0.25:
        coop = "The interaction was mostly defect-oriented, so the score reflects conflict/exploitation more than stable cooperation."
    else:
        coop = "The pair mixed cooperation and defection; inspect each cooperation rate to see who drove that pattern."
    return f"{outcome} {coop} A winner here is contextual, not a claim that the strategy is universally best."


def interpret_tournament(rows: Sequence[TournamentRow]) -> str:
    if not rows:
        return "No tournament result to interpret."
    leader = rows[0]
    spread = leader.score - rows[-1].score if len(rows) > 1 else 0.0
    return (f"{leader.strategy} ranked first by aggregate payoff across this field. "
            f"The top-to-bottom score spread is {spread:.2f}. Tournament rank depends on the opponents included, "
            "turn length, repetitions, payoff rules, and seed; rerun with other fields before calling a strategy dominant.")


def interpret_evolution(snapshots: Sequence[EvolutionSnapshot]) -> str:
    if not snapshots:
        return "No evolution result to interpret."
    start, end = snapshots[0].populations, snapshots[-1].populations
    winner = max(end, key=end.get)
    delta = end[winner] - start.get(winner, 0)
    extinct = [n for n, v in end.items() if v == 0]
    text = (f"{winner} has the largest final population ({end[winner]}) and changed by {delta:+d} individuals. "
            "Population growth means the strategy reproduced more successfully in this simulated environment; it does not prove universal superiority.")
    if extinct:
        text += " Extinct in this run: " + ", ".join(extinct) + "."
    return text
