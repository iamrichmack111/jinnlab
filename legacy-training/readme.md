Sure! Here's a README document that you can use to describe your Axelrod tournament code, which includes the Suspicious Grudger strategy along with other strategies. This README provides an overview, installation instructions, how to run the code, and an explanation of the output.

---

### README - Axelrod Tournament Code

#### Overview
This Python script runs a simulation of an iterated prisoner's dilemma tournament using the Axelrod library. The tournament features three distinct strategies:
1. **Suspicious Grudger**: Begins by defecting and continues to do so if the opponent ever defects. If the opponent cooperates, Suspicious Grudger will cooperate until the opponent defects.
2. **Random**: Cooperates or defects randomly.
3. **Cooperator**: Always cooperates.

The purpose of this tournament is to observe how different strategies perform against each other under repeated game conditions, focusing on metrics such as cooperation rate, partner reliability, and strategic effectiveness.

#### Requirements
- Python 3.x
- Axelrod Library

#### Installation
First, ensure that Python 3 is installed on your system. You can download Python from [python.org](https://www.python.org/downloads/).

Next, install the Axelrod library using pip:

```bash
pip install axelrod
```

#### Running the Tournament
To run the tournament, save the following script to a file, for example, `tournament.py`. Ensure the Axelrod library is installed as mentioned above.

Here's the complete script to include in `tournament.py`:

```python
import axelrod as axl
from axelrod import Action

C, D = Action.C, Action.D

class SuspiciousGrudger(axl.Player):
    name = "Suspicious Grudger"
    def strategy(self, opponent):
        if not self.history:
            return D
        if D in opponent.history:
            return D
        return C

players = [SuspiciousGrudger(), axl.Random(), axl.Cooperator()]
tournament = axl.Tournament(players, repetitions=10000)
results = tournament.play()

for player in players:
    index = players.index(player)
    print(f"\nResults for {player.name}:")
    print(f"  Cooperating Rating: {results.cooperating_rating[index]}")
    print(f"  Good Partner Rating: {results.good_partner_rating[index]}")
    print(f"  Eigenjesus Rating: {results.eigenjesus_rating[index]}")
    print(f"  Eigenmoses Rating: {results.eigenmoses_rating[index]}")

winner_index = results.ranking.index(0)
winner = players[winner_index]
print(f"\nWinner of the Tournament: {winner.name}")
```

To run the script, navigate to the directory containing `tournament.py` and run:

```bash
python tournament.py
```

#### Output Explanation
The script outputs the following for each strategy:
- **Cooperating Rating**: Indicates the percentage of cooperation moves.
- **Good Partner Rating**: Reflects how often the strategy cooperated at least as much as its opponents.
- **Eigenjesus Rating**: Measures the strategy's "niceness" based on eigenvector centrality.
- **Eigenmoses Rating**: Evaluates how effectively the strategy maximizes its own payoff while minimizing opponents' payoffs.

Finally, the script announces the winner of the tournament based on the overall performance scores.

#### Conclusion
This README provides the necessary details to run and understand the outcomes of the iterated prisoner's dilemma tournament using the Axelrod library. The script allows users to observe strategic behavior across multiple interactions, offering insights into competitive and cooperative dynamics within game theory.

---

