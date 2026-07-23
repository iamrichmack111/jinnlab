from jinnlab.db import ResultsDB

def test_insert_summary_and_export(tmp_path):
    db = ResultsDB(tmp_path / "test.db")
    eid = db.add_experiment(experiment_type="match", player1="A", player2="B", winner="A", score1=5, score2=3, seed=7)
    assert eid == 1
    s = db.summary()
    assert s["total"] == 1
    assert s["avg_margin"] == 2
    out = tmp_path / "out.csv"
    assert db.export_csv(out) == 1
    assert "experiment_type" in out.read_text()

def test_strategy_notes_are_associated_with_strategy(tmp_path):
    db = ResultsDB(tmp_path / "notes.db")
    assert db.get_strategy_note("Tit For Tat") == ""
    db.save_strategy_note("Tit For Tat", "Strong reciprocal baseline")
    db.save_strategy_note("Defector", "Useful adversarial control")
    assert db.get_strategy_note("Tit For Tat") == "Strong reciprocal baseline"
    assert db.get_strategy_note("Defector") == "Useful adversarial control"
    db.save_strategy_note("Tit For Tat", "Updated observation")
    assert db.get_strategy_note("Tit For Tat") == "Updated observation"

def test_notebook_and_strategy_lineage(tmp_path):
    db = ResultsDB(tmp_path / "research.db")
    eid = db.add_experiment(experiment_type="match", player1="A", player2="B", winner="A")
    db.save_experiment_note(eid, "hypothesis", "observation", "conclusion")
    assert db.get_experiment_note(eid)["conclusion"] == "conclusion"
    assert db.save_strategy_design("Richmack", {"opening":"C","retaliation":2}) == "Richmack v1"
    assert db.save_strategy_design("Richmack", {"opening":"D","retaliation":1}) == "Richmack v2"
    assert [d["version"] for d in db.strategy_designs()] == [1, 2]
