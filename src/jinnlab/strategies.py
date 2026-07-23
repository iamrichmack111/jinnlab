from __future__ import annotations


def custom_strategy_classes():
    """Return built-in custom Axelrod Player classes, importing Axelrod lazily."""
    import axelrod as axl
    C, D = axl.Action.C, axl.Action.D

    class Jeremy(axl.Player):
        """Defect first, forgive initially, then defect forever after 3 defections."""
        name = "Jinn: Three Strikes"
        classifier = {"memory_depth": float("inf"), "stochastic": False,
                      "long_run_time": False, "inspects_source": False,
                      "manipulates_source": False, "manipulates_state": False}

        def __init__(self):
            super().__init__(); self.defections_count = 0; self.defect_forever = False

        def strategy(self, opponent):
            if not self.history: return D
            if self.defect_forever: return D
            if opponent.history and opponent.history[-1] == D: self.defections_count += 1
            if self.defections_count >= 3:
                self.defect_forever = True; return D
            return C

    class SuspiciousGrudger(axl.Player):
        """Defect first; cooperate only while the opponent has never defected."""
        name = "Jinn: Suspicious Grudger"
        classifier = {"memory_depth": float("inf"), "stochastic": False,
                      "long_run_time": False, "inspects_source": False,
                      "manipulates_source": False, "manipulates_state": False}

        def strategy(self, opponent):
            if not self.history: return D
            if D in opponent.history: return D
            return C

    return [Jeremy, SuspiciousGrudger]


def build_rule_strategy(design: dict):
    """Build a simple, safe rule-based Axelrod strategy from persisted settings."""
    import axelrod as axl
    C, D = axl.Action.C, axl.Action.D
    name = design.get("display_name") or design.get("name") or "Custom Rule Strategy"
    opening = design.get("opening", "C")
    retaliation = max(0, int(design.get("retaliation", 1)))
    forgive_after = max(0, int(design.get("forgive_after", 0)))
    defection_probability = min(1.0, max(0.0, float(design.get("random_defection", 0.0))))

    class RuleStrategy(axl.Player):
        """User-designed rule strategy created in JinnLab's Strategy Designer."""
        classifier = {"memory_depth": float("inf"), "stochastic": defection_probability > 0,
                      "long_run_time": False, "inspects_source": False,
                      "manipulates_source": False, "manipulates_state": False}

        def __init__(self):
            super().__init__(); self.retaliation_left = 0; self.coop_streak = 0

        def strategy(self, opponent):
            if not self.history:
                return C if opening == "C" else D
            if opponent.history[-1] == D:
                self.retaliation_left = retaliation
                self.coop_streak = 0
            else:
                self.coop_streak += 1
            if forgive_after and self.coop_streak >= forgive_after:
                self.retaliation_left = 0
            if self.retaliation_left > 0:
                self.retaliation_left -= 1
                return D
            if defection_probability and self._random.random() < defection_probability:
                return D
            return C

    RuleStrategy.name = name
    return RuleStrategy
