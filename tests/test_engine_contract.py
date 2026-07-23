from jinnlab.engine import MatchResult, TournamentRow

def test_result_models():
    r = MatchResult("A", "B", 3, 2, "A", .5, .4)
    assert r.winner == "A"
    t = TournamentRow(1, "A", 99)
    assert t.rank == 1
