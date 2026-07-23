from __future__ import annotations

import json
import os
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, ListItem, ListView, Markdown, Select, Static, TabbedContent, TabPane, TextArea

from .db import ResultsDB
from .engine import (interpret_evolution, interpret_match, interpret_tournament,
                     run_match, run_matrix, run_moran, run_population_evolution,
                     run_tournament, strategy_catalog, strategy_info)

DATA_DIR = Path(os.environ.get("JINNLAB_DATA", "~/.local/share/jinnlab")).expanduser()
DB_PATH = DATA_DIR / "jinnlab.db"
EXPORT_PATH = DATA_DIR / "exports" / "experiments.csv"

GUIDE = """# How to use and interpret JinnLab

JinnLab is an **experimental workbench**, not a universal strategy-ranking oracle. Results describe the conditions you chose.

## Recommended workflow
1. Start in **Match** to learn how two strategies interact.
2. Use **Matrix** to see who exploits or cooperates with whom.
3. Use **Tournament** to rank a field by total payoff.
4. Use **Evolution** to test whether success persists under reproduction and competition.
5. Use **Batch** with more repetitions/seeds to check robustness.
6. Record your hypothesis, observation, and conclusion in **Notebook**.

## Core metrics
**Score** is cumulative Prisoner's Dilemma payoff. Higher is better inside that experiment. Compare scores only when turns and payoff rules are comparable.

**Cooperation rate** is the fraction of moves that were cooperation. High cooperation can produce strong mutual payoff, but a cooperative strategy can also be exploited.

**Tournament aggregate score** adds performance across the chosen opponents. A first-place strategy may fall in rank if the field changes.

**Population share** in Evolution is simulated reproductive success. Growth means the strategy performed well against that population under those parameters—not that it is always optimal.

**Seed** makes stochastic runs reproducible. Use the same seed to reproduce a run; change seeds to test sensitivity.

**Repetitions** reduce the chance that a stochastic result is a fluke. For serious comparisons, use more repetitions and multiple seeds.

## Reading outcomes responsibly
Look for patterns that survive changes in opponent mix, turns, population, mutation, and seed. A robust strategy should perform well across multiple experiments, not just one favorable setup.
"""


class JinnLab(App):
    TITLE = "JinnLab 3.3.3"
    SUB_TITLE = "Evolutionary Game Theory Research Workbench"
    BINDINGS = [
        ("q", "quit", "Quit"), ("m", "start_match", "Start Match"), ("b", "start_batch", "Run Batch"), ("d", "save_designer", "Save Design"),
        ("r", "refresh_history", "Refresh"), ("e", "export", "Export CSV"),
        ("1", "tab('match')", "Match"), ("2", "tab('batch')", "Batch"),
        ("3", "tab('matrix')", "Matrix"), ("4", "tab('evolution')", "Evolution"),
        ("5", "tab('tournament')", "Tournament"), ("6", "tab('designer')", "Designer"),
        ("7", "tab('strategies')", "Strategies"), ("8", "tab('notebook')", "Notebook"),
        ("9", "tab('guide')", "Guide"),
    ]

    CSS = """
    Screen { layout: vertical; }
    .controls { height: auto; padding: 1; }
    .field { width: 1fr; margin-right: 1; }
    .actions { height: 4; min-height: 4; padding: 0 1; }
    .primary-action { width: 24; min-width: 20; }
    .scroll { height: 1fr; }
    .hint { height: auto; padding: 0 1 1 1; }
    .result { height: auto; min-height: 7; padding: 1; }
    .explain { height: auto; min-height: 6; padding: 1; }
    DataTable { height: 1fr; }
    #strategy-list { width: 32; }
    #strategy-detail-pane { width: 1fr; padding: 1; }
    #strategy-note { height: 8; }
    #matrix-picker { width: 1fr; }
    #matrix-selected { height: 3; min-height: 3; padding: 0 1; }
    #matrix-table { height: 15; min-height: 10; }
    #hypothesis, #observation, #conclusion { height: 6; }
    #status { height: 1; dock: bottom; }
    """

    def __init__(self):
        super().__init__()
        self.db = ResultsDB(DB_PATH)
        self.reload_catalog()
        self.matrix_selected = [
            self._default("Tit For Tat"),
            self._default("Defector", 1),
            self._default("Grudger", 2),
            self._default("Cooperator", 3),
        ]

    def reload_catalog(self):
        self.catalog = strategy_catalog(self.db.strategy_designs())
        self.names = list(self.catalog)

    def _default(self, wanted: str, fallback: int = 0):
        for n in self.names:
            if n.lower() == wanted.lower(): return n
        return self.names[min(fallback, len(self.names)-1)]

    def compose(self) -> ComposeResult:
        options = [(n, n) for n in self.names]
        yield Header()
        with TabbedContent(initial="match"):
            with TabPane("Match", id="match"):
                with VerticalScroll(classes="scroll"):
                    yield Markdown("## Match Lab\n**Step 1:** choose Player 1 and Player 2. **Step 2:** set turns/repetitions/seed. **Step 3:** press the green **Start Match** button or press **m**. The result and explanation stay on this page directly below the button.")
                    with Horizontal(classes="controls"):
                        for label, wid, value in [("Player 1", "p1", self._default("Tit For Tat")), ("Player 2", "p2", self._default("Defector", 1))]:
                            with Vertical(classes="field"):
                                yield Label(label); yield Select(options, value=value, id=wid)
                        for label, wid, value in [("Turns", "turns", "200"), ("Repetitions", "reps", "10"), ("Seed", "seed", "10000")]:
                            with Vertical(classes="field"):
                                yield Label(label); yield Input(value, type="integer", id=wid)
                    yield Static("Turns = moves per game. Repetitions = how many times to repeat the matchup. Seed = reproducible randomness; keep it the same to reproduce a result.", classes="hint")
                    with Horizontal(classes="actions"):
                        yield Button("▶ START MATCH", id="start-match", variant="success", classes="primary-action")
                        yield Button("Run Moran Evolution", id="run-moran", variant="primary")
                    yield Static("MATCH RESULT WILL APPEAR HERE\nNo match run yet.", id="match-result", classes="result")
                    yield Markdown("### How to interpret the result\nRun a match and JinnLab will explain the winner, score difference, cooperation rate, and what you should *not* conclude from one matchup.", id="match-explain", classes="explain")

            with TabPane("Batch", id="batch"):
                with VerticalScroll(classes="scroll"):
                    yield Markdown("## Batch Experiment Builder\n**Purpose:** test several strategies across multiple random seeds instead of trusting one run.\n\n**Step 1:** enter strategy names separated by commas. **Step 2:** set turns, repetitions and number of seeds. **Step 3:** press **RUN BATCH** or press **b**. Results rank the strategies by average aggregate tournament score.")
                    with Vertical(classes="controls"):
                        yield Label("Strategies (comma separated)")
                        yield Input("Tit For Tat,Defector,Grudger,Cooperator", id="batch-strategies", placeholder="Strategy A,Strategy B,...")
                        with Horizontal():
                            with Vertical(classes="field"):
                                yield Label("Turns per match")
                                yield Input("200", id="batch-turns", type="integer")
                            with Vertical(classes="field"):
                                yield Label("Repetitions per pairing")
                                yield Input("5", id="batch-reps", type="integer")
                            with Vertical(classes="field"):
                                yield Label("How many seeds")
                                yield Input("3", id="batch-seeds", type="integer")
                            with Vertical(classes="field"):
                                yield Label("Starting seed")
                                yield Input("10000", id="batch-seed", type="integer")
                    yield Static("Example: 3 seeds starting at 10000 runs the field with seeds 10000, 10001 and 10002. More seeds/repetitions make conclusions more robust but take longer.", classes="hint")
                    with Horizontal(classes="actions"):
                        yield Button("▶ RUN BATCH", id="run-batch", variant="success", classes="primary-action")
                    yield DataTable(id="batch-table")
                    yield Markdown("### How to interpret batch results\nThe top row has the highest **average aggregate score across seeds**. A tiny lead may be noise; increase seeds/repetitions. A strategy that stays near the top across many seeds is stronger evidence of robust performance.", id="batch-explain", classes="explain")

            with TabPane("Matrix", id="matrix"):
                with VerticalScroll(classes="scroll"):
                    yield Markdown("## Strategy Comparison Matrix\nUse the single dropdown to add strategies to the field. This keeps the controls compact so the score matrix remains visible. You can compare **2 to 12 strategies**.\n\nThe matrix includes each matchup score plus **Total** and **Average** row scores, restoring the ranking information from the earlier version.")
                    with Horizontal(classes="controls"):
                        with Vertical(classes="field"):
                            yield Label("Add strategy")
                            yield Select(options, value=self._default("Tit For Tat"), id="matrix-picker")
                        with Vertical(classes="field"):
                            yield Label("Turns")
                            yield Input("60", id="matrix-turns", type="integer")
                        with Vertical(classes="field"):
                            yield Label("Repetitions")
                            yield Input("1", id="matrix-reps", type="integer")
                        with Vertical(classes="field"):
                            yield Label("Seed")
                            yield Input("10000", id="matrix-seed", type="integer")
                    with Horizontal(classes="actions"):
                        yield Button("+ Add", id="matrix-add", variant="primary")
                        yield Button("Remove Last", id="matrix-remove")
                        yield Button("Clear", id="matrix-clear")
                        yield Button("Defaults", id="reset-matrix")
                        yield Button("▶ BUILD MATRIX", id="run-matrix", variant="success", classes="primary-action")
                    yield Static("", id="matrix-selected")
                    yield Static("4 strategies selected. Matrix size: 4 × 4.", id="matrix-selection-status", classes="hint")
                    yield DataTable(id="matrix-table")
                    yield Static("Tip: use the arrow keys / horizontal scroll to inspect wide matrices and the Total/Average columns.", classes="hint")
                    yield Markdown("### How to read it\nEach matchup cell is the row strategy's score against the column strategy. **Total** adds that row across the field; **Average** divides by the number of opponents shown. Compare reciprocal cells to spot exploitation versus mutual benefit.", id="matrix-explain", classes="explain")

            with TabPane("Evolution", id="evolution"):
                yield Markdown("## Evolution Lab\nPopulation format: `Tit For Tat=40,Defector=30,Cooperator=20,Grudger=10`.")
                yield Input("Tit For Tat=40,Defector=30,Cooperator=20,Grudger=10", id="population")
                with Horizontal(classes="controls"):
                    yield Input("100", id="generations", type="integer", placeholder="Generations")
                    yield Input("60", id="evo-turns", type="integer", placeholder="Turns/match")
                    yield Input("0.01", id="mutation", placeholder="Mutation rate")
                    yield Input("10000", id="evo-seed", type="integer", placeholder="Seed")
                yield Button("Run Population Evolution", id="run-evolution", variant="success")
                yield DataTable(id="evolution-table")
                yield Markdown("**Interpretation:** Run evolution to see which strategies gain or lose population share.", id="evolution-explain", classes="explain")

            with TabPane("Tournament", id="tournament"):
                yield Markdown("## Tournament Mode\nEnter a field explicitly; rankings are aggregate payoff against every other strategy in that field.")
                yield Input("Tit For Tat,Defector,Grudger,Cooperator,Jinn: Three Strikes", id="tournament-strategies")
                yield Button("Run Tournament", id="run-tournament", variant="primary")
                yield DataTable(id="tournament-table")
                yield Markdown("**Interpretation:** Tournament rank is field-dependent. Run different opponent mixes before declaring a strategy strongest.", id="tournament-explain", classes="explain")

            with TabPane("Designer", id="designer"):
                with VerticalScroll(classes="scroll"):
                    yield Markdown("## Strategy Designer + Lineage\nBuild a simple custom strategy without writing Python. Each time you save the same family name, JinnLab creates a new version (`v1`, `v2`, `v3`...).\n\n### What each setting means\n- **Family name**: the strategy's name, for example `Richmack`.\n- **Opening move**: what it does on the first turn. `Cooperate` is friendly; `Defect` is aggressive.\n- **Retaliation rounds**: after the opponent defects, how many rounds your strategy defects back. `2` means retaliate for two turns.\n- **Forgive after N cooperative rounds**: how many cooperative opponent moves are needed before hostility is reset. `0` disables this forgiveness rule.\n- **Random defection probability**: chance of defecting due to noise. **`0.02` means 2%, not 2.0 turns.** `0` means never random-defect; `0.10` means 10%.\n\nStart with the defaults, save it, then change one setting at a time and compare versions using the same Match/Batch/Tournament parameters.")
                    with Vertical(classes="controls"):
                        yield Label("1. Strategy family name")
                        yield Input("Richmack", id="design-name", placeholder="Example: Richmack")
                        yield Label("2. Opening move")
                        yield Select([("Cooperate", "C"), ("Defect", "D")], value="C", id="design-opening")
                        yield Label("3. Retaliation rounds after opponent defects")
                        yield Input("2", id="design-retaliation", type="integer", placeholder="Example: 2")
                        yield Label("4. Forgive after this many cooperative rounds (0 = disabled)")
                        yield Input("3", id="design-forgive", type="integer", placeholder="Example: 3")
                        yield Label("5. Random defection probability (decimal from 0 to 1)")
                        yield Input("0.02", id="design-random", placeholder="0.02 = 2%; 0.10 = 10%")
                    yield Static("Example default behavior: cooperate first → if the opponent defects, retaliate for 2 rounds → after 3 cooperative opponent rounds, forgive/reset → on any eligible turn there is a 2% random-defection chance.", classes="hint")
                    with Horizontal(classes="actions"):
                        yield Button("💾 SAVE NEW VERSION", id="save-design", variant="success", classes="primary-action")
                    yield DataTable(id="design-table")
                    yield Markdown("### What to do after saving\n1. Restart JinnLab so the new version appears in strategy selectors. 2. Match it against Cooperator, Defector and Tit For Tat. 3. Run Batch/Tournament using the same seeds as the previous version. 4. Record why the new version improved or regressed in the Notebook.\n\n**Interpretation:** retaliation can discourage exploitation but excessive retaliation can trap two strategies in mutual defection. Forgiveness can restore cooperation but may invite repeated exploitation. Random defection models mistakes/noise and can reveal whether a strategy is resilient.", classes="explain")

            with TabPane("Strategies", id="strategies"):
                with Horizontal():
                    yield ListView(*[ListItem(Label(n)) for n in self.names], id="strategy-list")
                    with Vertical(id="strategy-detail-pane"):
                        yield Markdown("Select a strategy to inspect its behavior.", id="strategy-detail")
                        yield Label("Strategy Notes")
                        yield TextArea(id="strategy-note")
                        with Horizontal(classes="actions"):
                            yield Button("Save Note", id="save-strategy-note", variant="primary")
                            yield Button("Clear", id="clear-strategy-note")
                        yield Static("Notes stay linked to the selected strategy.", id="strategy-note-status")

            with TabPane("Notebook", id="notebook"):
                yield Markdown("## Reproducible Experiment Notebook\nEvery persisted run has an ID. Enter it below to load its configuration and research notes.")
                with Horizontal(classes="controls"):
                    yield Input("", id="experiment-id", type="integer", placeholder="Experiment ID")
                    yield Button("Load", id="load-experiment")
                    yield Button("Rerun Match", id="rerun-experiment", variant="primary")
                yield Markdown("No experiment loaded.", id="experiment-detail")
                yield Label("Hypothesis"); yield TextArea(id="hypothesis")
                yield Label("Observation"); yield TextArea(id="observation")
                yield Label("Conclusion"); yield TextArea(id="conclusion")
                yield Button("Save Notebook Entry", id="save-notebook", variant="success")
                yield DataTable(id="history-table")

            with TabPane("Analytics", id="analytics"):
                yield Markdown(id="analytics-md")

            with TabPane("Guide", id="guide"):
                yield Markdown(GUIDE)

        yield Static(f"Database: {DB_PATH}", id="status")
        yield Footer()

    def on_mount(self):
        self.setup_tables(); self.refresh_history(); self.refresh_analytics(); self.refresh_designs(); self._update_matrix_selection_status()

    def setup_tables(self):
        self.query_one("#tournament-table", DataTable).add_columns("Rank", "Strategy", "Aggregate Score")
        self.query_one("#batch-table", DataTable).add_columns("Rank", "Strategy", "Average aggregate", "Seeds")
        self.query_one("#evolution-table", DataTable).add_columns("Generation", "Population")
        self.query_one("#history-table", DataTable).add_columns("ID", "Time", "Type", "P1", "P2", "Winner", "Score")
        self.query_one("#design-table", DataTable).add_columns("Family", "Version", "Display name", "Opening", "Retaliate", "Forgive", "Random D")

    def action_tab(self, tab_id: str): self.query_one(TabbedContent).active = tab_id

    def _match_inputs(self):
        p1=str(self.query_one("#p1",Select).value); p2=str(self.query_one("#p2",Select).value)
        turns=max(1,int(self.query_one("#turns",Input).value or 200)); reps=max(1,int(self.query_one("#reps",Input).value or 1))
        s=self.query_one("#seed",Input).value.strip(); seed=int(s) if s else None
        return p1,p2,turns,reps,seed

    def _names_from(self, selector: str):
        raw=self.query_one(selector,Input).value
        names=[x.strip() for x in raw.split(",") if x.strip()]
        unknown=[n for n in names if n not in self.catalog]
        if unknown: raise ValueError("Unknown strategy: " + ", ".join(unknown))
        if len(names)<2: raise ValueError("Choose at least two strategies")
        return names

    def action_start_match(self):
        self.query_one(TabbedContent).active="match"
        try: params=self._match_inputs()
        except Exception as e: self.notify(str(e),severity="error"); return
        self.run_match_worker(*params)

    @on(Button.Pressed,"#start-match")
    def start_match_button(self): self.action_start_match()

    @work(thread=True, exclusive=True, group="simulation")
    def run_match_worker(self,p1,p2,turns,reps,seed):
        try:
            result=run_match(p1,p2,turns,reps,seed,self.catalog)
            eid=self.db.add_experiment(experiment_type="match",player1=p1,player2=p2,winner=result.winner,score1=result.score1,score2=result.score2,turns=turns,repetitions=reps,seed=seed,metadata=json.dumps({"cooperation1":result.cooperation1,"cooperation2":result.cooperation2}))
            text=f"Experiment #{eid}\nWinner: {result.winner}\nAverage total score: {p1} {result.score1:.2f} — {p2} {result.score2:.2f}\nCooperation: {p1} {result.cooperation1:.1%} — {p2} {result.cooperation2:.1%}\nTurns {turns} | Repetitions {reps} | Seed {seed}"
            explanation="### What this result means\n"+interpret_match(result,turns)
            self.call_from_thread(self.query_one("#match-result",Static).update,text); self.call_from_thread(self.query_one("#match-explain",Markdown).update,explanation)
            self.call_from_thread(self.refresh_history); self.call_from_thread(self.refresh_analytics)
        except Exception as e: self.call_from_thread(self.notify,str(e),severity="error")

    @on(Button.Pressed,"#run-moran")
    def start_moran(self):
        try: p1,p2,_,_,seed=self._match_inputs()
        except Exception as e: self.notify(str(e),severity="error"); return
        self.moran_worker(p1,p2,seed)

    @work(thread=True, exclusive=True, group="simulation")
    def moran_worker(self,p1,p2,seed):
        try:
            winner,generations=run_moran(p1,p2,seed,self.catalog)
            eid=self.db.add_experiment(experiment_type="moran",player1=p1,player2=p2,winner=winner,seed=seed,metadata=json.dumps({"generations":generations}))
            self.call_from_thread(self.query_one("#match-result",Static).update,f"Moran experiment #{eid}\nFixation winner: {winner}\nGenerations to absorption: {generations}\nSeed: {seed}")
            self.call_from_thread(self.query_one("#match-explain",Markdown).update,f"### What this means\n**{winner}** reached fixation in this two-strategy stochastic population after {generations} generations. Fixation is sensitive to population setup and randomness, so repeat with multiple seeds.")
            self.call_from_thread(self.refresh_history)
        except Exception as e: self.call_from_thread(self.notify,str(e),severity="error")

    @on(Button.Pressed,"#run-tournament")
    def start_tournament(self):
        try: names=self._names_from("#tournament-strategies"); _,_,turns,reps,seed=self._match_inputs()
        except Exception as e: self.notify(str(e),severity="error"); return
        self.tournament_worker(names,turns,reps,seed)

    @work(thread=True,exclusive=True,group="simulation")
    def tournament_worker(self,names,turns,reps,seed):
        try:
            rows=run_tournament(names,turns,reps,seed,self.catalog)
            eid=self.db.add_experiment(experiment_type="tournament",winner=rows[0].strategy,turns=turns,repetitions=reps,seed=seed,metadata=json.dumps({"strategies":names}))
            self.db.add_tournament_scores(eid,[(eid,r.rank,r.strategy,r.score) for r in rows])
            def update():
                t=self.query_one("#tournament-table",DataTable); t.clear()
                for r in rows:t.add_row(str(r.rank),r.strategy,f"{r.score:.2f}")
                self.query_one("#tournament-explain",Markdown).update("### What this result means\n"+interpret_tournament(rows)); self.refresh_history(); self.refresh_analytics()
            self.call_from_thread(update)
        except Exception as e:self.call_from_thread(self.notify,str(e),severity="error")

    def action_start_batch(self):
        self.query_one(TabbedContent).active="batch"
        self.start_batch()

    def action_save_designer(self):
        self.query_one(TabbedContent).active="designer"
        self.save_design()

    @on(Button.Pressed,"#run-batch")
    def start_batch(self):
        try:
            names=self._names_from("#batch-strategies"); turns=max(1,int(self.query_one("#batch-turns",Input).value)); reps=max(1,int(self.query_one("#batch-reps",Input).value)); nseeds=max(1,int(self.query_one("#batch-seeds",Input).value)); base=int(self.query_one("#batch-seed",Input).value or 0)
        except Exception as e:self.notify(str(e),severity="error");return
        self.batch_worker(names,turns,reps,nseeds,base)

    @work(thread=True,exclusive=True,group="simulation")
    def batch_worker(self,names,turns,reps,nseeds,base):
        try:
            totals={n:[] for n in names}
            for s in range(nseeds):
                rows=run_tournament(names,turns,reps,base+s,self.catalog)
                for r in rows:totals[r.strategy].append(r.score)
            ranked=sorted(((n,sum(v)/len(v)) for n,v in totals.items()),key=lambda x:-x[1])
            eid=self.db.add_experiment(experiment_type="batch",winner=ranked[0][0],turns=turns,repetitions=reps,seed=base,metadata=json.dumps({"strategies":names,"seeds":nseeds,"averages":dict(ranked)}))
            def update():
                t=self.query_one("#batch-table",DataTable);t.clear()
                for i,(n,score) in enumerate(ranked,1):t.add_row(str(i),n,f"{score:.2f}",str(nseeds))
                gap=ranked[0][1]-ranked[1][1] if len(ranked)>1 else 0
                self.query_one("#batch-explain",Markdown).update(f"### What this result means\n**{ranked[0][0]}** has the highest average aggregate score across {nseeds} seeds. Its lead over second place is {gap:.2f}. Small leads deserve more seeds/repetitions; stable large leads are stronger evidence.")
                self.refresh_history();self.refresh_analytics()
            self.call_from_thread(update)
        except Exception as e:self.call_from_thread(self.notify,str(e),severity="error")

    def _matrix_names(self):
        names = list(dict.fromkeys(self.matrix_selected))
        if len(names) < 2:
            raise ValueError("Choose at least two strategies for the Matrix")
        if len(names) > 12:
            raise ValueError("Matrix supports up to 12 strategies")
        return names

    def _matrix_inputs(self):
        names = self._matrix_names()
        turns = max(1, int(self.query_one("#matrix-turns", Input).value or 60))
        reps = max(1, int(self.query_one("#matrix-reps", Input).value or 1))
        seed_text = self.query_one("#matrix-seed", Input).value.strip()
        seed = int(seed_text) if seed_text else None
        return names, turns, reps, seed

    def _update_matrix_selection_status(self):
        count = len(self.matrix_selected)
        self.query_one("#matrix-selection-status", Static).update(
            f"{count} strategies selected. Matrix size: {count} × {count}."
            if count >= 2 else f"{count} selected. Choose at least 2 strategies."
        )
        shown = "  •  ".join(self.matrix_selected) if self.matrix_selected else "No strategies selected."
        self.query_one("#matrix-selected", Static).update(shown)

    @on(Button.Pressed,"#matrix-add")
    def matrix_add_strategy(self):
        name = str(self.query_one("#matrix-picker", Select).value or "").strip()
        if not name:
            return
        if name in self.matrix_selected:
            self.notify(f"{name} is already selected", severity="warning")
            return
        if len(self.matrix_selected) >= 12:
            self.notify("Matrix supports up to 12 strategies", severity="warning")
            return
        self.matrix_selected.append(name)
        self._update_matrix_selection_status()

    @on(Button.Pressed,"#matrix-remove")
    def matrix_remove_strategy(self):
        if self.matrix_selected:
            self.matrix_selected.pop()
        self._update_matrix_selection_status()

    @on(Button.Pressed,"#matrix-clear")
    def matrix_clear_strategies(self):
        self.matrix_selected = []
        self.query_one("#matrix-table", DataTable).clear(columns=True)
        self._update_matrix_selection_status()

    @on(Button.Pressed,"#reset-matrix")
    def reset_matrix(self):
        self.matrix_selected = [
            self._default("Tit For Tat"),
            self._default("Defector", 1),
            self._default("Grudger", 2),
            self._default("Cooperator", 3),
        ]
        self.query_one("#matrix-turns", Input).value = "60"
        self.query_one("#matrix-reps", Input).value = "1"
        self.query_one("#matrix-seed", Input).value = "10000"
        self.query_one("#matrix-table", DataTable).clear(columns=True)
        self.query_one("#matrix-explain", Markdown).update(
            "### How to read it\nAdd strategies with the dropdown, then build the matrix. "
            "Total and Average summarize each row's field performance."
        )
        self._update_matrix_selection_status()

    @on(Button.Pressed,"#run-matrix")
    def start_matrix(self):
        try:
            names, turns, reps, seed = self._matrix_inputs()
        except Exception as e:
            self.notify(str(e),severity="error")
            return
        slow = []
        for name in names:
            try:
                if str(strategy_info(name, self.catalog).get("long_run", "False")).lower() == "true":
                    slow.append(name)
            except Exception:
                pass
        warning = ""
        if slow:
            warning = "\n\n⚠ Long-running strategy detected: " + ", ".join(slow) + ". This pairing may take much longer."
        total_pairs = len(names) * (len(names) + 1) // 2
        self.query_one("#matrix-explain", Markdown).update(
            f"### Running…\n0/{total_pairs} pairings complete. Building a {len(names)} × {len(names)} matrix "
            f"with {turns} turns and {reps} repetition(s).{warning}"
        )
        self.matrix_worker(names,turns,reps,seed)

    @work(thread=True,exclusive=True,group="simulation")
    def matrix_worker(self,names,turns,reps,seed):
        try:
            def progress(done, total, a, b):
                self.call_from_thread(
                    self.query_one("#matrix-explain", Markdown).update,
                    f"### Running…\n**{done}/{total} pairings complete** — last: `{a}` vs `{b}`. "
                    "If one pairing remains here for a long time, that strategy is computationally expensive; lower turns/repetitions for a quick scan."
                )

            matrix=run_matrix(names,turns,reps,seed,self.catalog,progress_callback=progress)
            best=max(names,key=lambda n:sum(matrix[n].values()))
            self.db.add_experiment(experiment_type="matrix",winner=best,turns=turns,repetitions=reps,seed=seed,metadata=json.dumps({"strategies":names,"matrix":matrix}))
            def update():
                old=self.query_one("#matrix-table",DataTable)
                old.clear(columns=True)
                old.add_columns("Strategy", *names, "Total", "Average")
                totals = {a: sum(matrix[a].values()) for a in names}
                avgs = {a: totals[a] / max(1, len(names)) for a in names}
                for a in names:
                    old.add_row(
                        a,
                        *[f"{matrix[a][b]:.1f}" for b in names],
                        f"{totals[a]:.1f}",
                        f"{avgs[a]:.2f}",
                    )
                ranked = sorted(names, key=lambda n: totals[n], reverse=True)
                leader = ranked[0]
                runner = ranked[1] if len(ranked) > 1 else None
                gap = totals[leader] - totals[runner] if runner else 0.0
                self.query_one("#matrix-explain",Markdown).update(
                    f"### Matrix complete\n**{leader}** ranks first with a total score of **{totals[leader]:.1f}** "
                    f"and an average of **{avgs[leader]:.2f}** per opponent."
                    + (f" The lead over **{runner}** is **{gap:.1f}** total points." if runner else "")
                    + "\n\nUse the individual cells to see *why* the leader scored well: mutual cooperation, exploitation, "
                      "or resilience against defectors. Increase repetitions for close rankings."
                )
                self.refresh_history();self.refresh_analytics()
            self.call_from_thread(update)
        except Exception as e:
            def failed():
                self.query_one("#matrix-explain",Markdown).update(f"### Matrix failed\n`{e}`\n\nChange the selection or lower turns/repetitions and run again.")
                self.notify(str(e),severity="error")
            self.call_from_thread(failed)

    @on(Button.Pressed,"#run-evolution")
    def start_evolution(self):
        try:
            pairs=[x.strip() for x in self.query_one("#population",Input).value.split(",") if x.strip()]; pop={}
            for pair in pairs:
                n,v=pair.rsplit("=",1); n=n.strip(); pop[n]=int(v)
                if n not in self.catalog:raise ValueError(f"Unknown strategy: {n}")
            generations=max(1,int(self.query_one("#generations",Input).value)); turns=max(1,int(self.query_one("#evo-turns",Input).value)); mutation=float(self.query_one("#mutation",Input).value); seed=int(self.query_one("#evo-seed",Input).value or 0)
        except Exception as e:self.notify(str(e),severity="error");return
        self.evolution_worker(pop,generations,turns,mutation,seed)

    @work(thread=True,exclusive=True,group="simulation")
    def evolution_worker(self,pop,generations,turns,mutation,seed):
        try:
            
            def progress(snapshot):
                def show():
                    t=self.query_one("#evolution-table",DataTable)
                    t.add_row(str(snapshot.generation),", ".join(f"{n}={v}" for n,v in snapshot.populations.items()))
                    self.query_one("#evolution-explain",Markdown).update(f"### Live interpretation\nGeneration **{snapshot.generation}** is complete. Watch which strategies steadily gain population rather than reacting to one temporary swing.")
                self.call_from_thread(show)
            self.call_from_thread(lambda: self.query_one("#evolution-table",DataTable).clear())
            snaps=run_population_evolution(pop,generations,turns,1,mutation,seed,self.catalog,max(1,generations//10),progress)
            final=snaps[-1].populations;winner=max(final,key=final.get)
            eid=self.db.add_experiment(experiment_type="evolution",winner=winner,turns=turns,seed=seed,metadata=json.dumps({"initial":pop,"generations":generations,"mutation":mutation,"snapshots":[{"generation":s.generation,"populations":s.populations} for s in snaps]}))
            def update():
                self.query_one("#evolution-explain",Markdown).update("### What this result means\n"+interpret_evolution(snaps)+f"\n\nExperiment #{eid}; mutation rate {mutation:.2%}; seed {seed}.")
                self.refresh_history();self.refresh_analytics()
            self.call_from_thread(update)
        except Exception as e:self.call_from_thread(self.notify,str(e),severity="error")

    @on(ListView.Selected,"#strategy-list")
    def strategy_selected(self,event:ListView.Selected):
        if event.list_view.index is None:return
        name=self.names[event.list_view.index];info=strategy_info(name,self.catalog)
        self.query_one("#strategy-detail",Markdown).update(f"# {name}\n\n{info['description']}\n\n**Memory depth:** {info['memory']}  \n**Stochastic:** {info['stochastic']}  \n**Long runtime:** {info['long_run']}\n\n### How to study it\nPair it with Cooperator, Defector, Tit For Tat, and one noisy strategy. Then use Tournament/Evolution to see whether its behavior generalizes beyond one opponent.")
        self.query_one("#strategy-note",TextArea).text=self.db.get_strategy_note(name);self.query_one("#strategy-note-status",Static).update(f"Notes linked to: {name}")

    def _selected_strategy_name(self):
        lv=self.query_one("#strategy-list",ListView); return None if lv.index is None else self.names[lv.index]

    @on(Button.Pressed,"#save-strategy-note")
    def save_strategy_note(self):
        n=self._selected_strategy_name()
        if not n:self.notify("Select a strategy first",severity="warning");return
        self.db.save_strategy_note(n,self.query_one("#strategy-note",TextArea).text.strip());self.notify(f"Saved note for {n}")

    @on(Button.Pressed,"#clear-strategy-note")
    def clear_strategy_note(self):
        n=self._selected_strategy_name()
        if not n:return
        self.query_one("#strategy-note",TextArea).text="";self.db.save_strategy_note(n,"")

    @on(Button.Pressed,"#save-design")
    def save_design(self):
        try:
            family=self.query_one("#design-name",Input).value.strip()
            if not family:
                raise ValueError("Enter a family name first, for example Richmack")
            definition={"opening":str(self.query_one("#design-opening",Select).value),"retaliation":int(self.query_one("#design-retaliation",Input).value or 0),"forgive_after":int(self.query_one("#design-forgive",Input).value or 0),"random_defection":float(self.query_one("#design-random",Input).value or 0)}
            display=self.db.save_strategy_design(family,definition)
            self.reload_catalog()
            self.refresh_designs()
            self.refresh_strategy_widgets()
            self.notify(f"Saved {display}. Use '{family}' for the latest version or '{display}' for this exact version.")
        except Exception as e:self.notify(str(e),severity="error")

    def refresh_strategy_widgets(self):
        """Refresh visible strategy controls after a design is saved."""
        if not self.is_mounted:
            return
        options=[(n,n) for n in self.names]
        for selector_id in ("#p1", "#p2"):
            try:
                select=self.query_one(selector_id,Select)
                current=str(select.value)
                select.set_options(options)
                if current in self.catalog:
                    select.value=current
            except Exception:
                pass
        try:
            picker=self.query_one("#matrix-picker",Select)
            current=str(picker.value or "")
            picker.set_options(options)
            if current in self.catalog:
                picker.value=current
            self.matrix_selected=[n for n in self.matrix_selected if n in self.catalog]
            self._update_matrix_selection_status()
        except Exception:
            pass
        try:
            lv=self.query_one("#strategy-list",ListView)
            lv.clear()
            for n in self.names:
                lv.append(ListItem(Label(n)))
        except Exception:
            pass

    def refresh_designs(self):
        if not self.is_mounted:return
        t=self.query_one("#design-table",DataTable);t.clear()
        for d in self.db.strategy_designs():t.add_row(d["family_name"],str(d["version"]),d["display_name"],d.get("opening","C"),str(d.get("retaliation",1)),str(d.get("forgive_after",0)),str(d.get("random_defection",0)))

    def refresh_history(self):
        if not self.is_mounted:return
        t=self.query_one("#history-table",DataTable);t.clear()
        for r in self.db.recent(200):
            score="" if r["score1"] is None else f"{r['score1']:.1f}-{r['score2']:.1f}"
            t.add_row(str(r["id"]),r["created_at"],r["experiment_type"],r["player1"] or "",r["player2"] or "",r["winner"] or "",score)

    def action_refresh_history(self):self.refresh_history();self.refresh_analytics();self.notify("Refreshed")

    @on(Button.Pressed,"#load-experiment")
    def load_experiment(self):
        try:eid=int(self.query_one("#experiment-id",Input).value);r=self.db.get_experiment(eid)
        except Exception as e:self.notify(str(e),severity="error");return
        if not r:self.notify("Experiment not found",severity="warning");return
        meta=json.loads(r["metadata"] or "{}")
        self.query_one("#experiment-detail",Markdown).update(f"### Experiment #{eid}\n**Type:** {r['experiment_type']}  \n**Created:** {r['created_at']}  \n**Players:** {r['player1'] or '-'} vs {r['player2'] or '-'}  \n**Winner:** {r['winner'] or '-'}  \n**Turns:** {r['turns'] or '-'} | **Repetitions:** {r['repetitions'] or '-'} | **Seed:** {r['seed']}\n\n`metadata`: `{json.dumps(meta,sort_keys=True)}`")
        note=self.db.get_experiment_note(eid)
        self.query_one("#hypothesis",TextArea).text=note["hypothesis"] if note else "";self.query_one("#observation",TextArea).text=note["observation"] if note else "";self.query_one("#conclusion",TextArea).text=note["conclusion"] if note else ""

    @on(Button.Pressed,"#save-notebook")
    def save_notebook(self):
        try:eid=int(self.query_one("#experiment-id",Input).value)
        except ValueError:self.notify("Enter an experiment ID",severity="warning");return
        self.db.save_experiment_note(eid,self.query_one("#hypothesis",TextArea).text,self.query_one("#observation",TextArea).text,self.query_one("#conclusion",TextArea).text);self.notify(f"Notebook saved for experiment #{eid}")

    @on(Button.Pressed,"#rerun-experiment")
    def rerun_experiment(self):
        try:eid=int(self.query_one("#experiment-id",Input).value);r=self.db.get_experiment(eid)
        except Exception as e:self.notify(str(e),severity="error");return
        if not r or r["experiment_type"]!="match":self.notify("Rerun currently supports saved match experiments.",severity="warning");return
        self.query_one(TabbedContent).active="match";self.run_match_worker(r["player1"],r["player2"],r["turns"] or 200,r["repetitions"] or 1,r["seed"])

    def refresh_analytics(self):
        if not self.is_mounted:return
        s=self.db.summary();types="\n".join(f"- **{r['experiment_type']}**: {r['n']}" for r in s["by_type"]) or "- None";wins="\n".join(f"- **{r['winner']}**: {r['n']} wins" for r in s["winners"]) or "- None"
        self.query_one("#analytics-md",Markdown).update(f"# Experiment Analytics\n\n**Total persisted experiments:** {s['total']}  \n**Mean head-to-head score margin:** {s['avg_margin']:.2f}\n\n## Runs by type\n{types}\n\n## Frequent winners\n{wins}\n\n### Interpretation\nWinner frequency is descriptive, not controlled evidence: strategies may have faced different opponents or parameters. For a fair comparison, use the Batch tab with the same field, turns, repetitions, and seed policy.")

    def action_export(self):
        n=self.db.export_csv(EXPORT_PATH);self.notify(f"Exported {n} experiments to {EXPORT_PATH}")


def main(): JinnLab().run()

if __name__=="__main__":main()
