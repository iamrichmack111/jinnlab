import axelrod as axl
from axelrod import Action

C, D = Action.C, Action.D

# Define the Suspicious Grudger Strategy
class SuspiciousGrudger(axl.Player):
    """
    A player starts by defecting and then cooperates if the opponent has cooperated in the previous round.
    However, if the opponent defects at any point, this player defects forever.
    """
    name = "Suspicious Grudger"

    def strategy(self, opponent):
        # Defect on the first move
        if not self.history:
            return D
        # If opponent ever defected, continue defecting
        if D in opponent.history:
            return D
        # Otherwise, cooperate
        return C

    def reset(self):
        super().reset()

# Define the players
players = [SuspiciousGrudger(), axl.Random(), axl.Cooperator()]

# Create a tournament
tournament = axl.Tournament(players, repetitions=10000)

# Play the tournament
results = tournament.play()

# Print results for each player
for player in players:
    index = players.index(player)
    print(f"\nResults for {player.name}:")
    print(f"  Cooperating Rating: {results.cooperating_rating[index]}")
    print(f"  Good Partner Rating: {results.good_partner_rating[index]}")
    print(f"  Eigenjesus Rating: {results.eigenjesus_rating[index]}")
    print(f"  Eigenmoses Rating: {results.eigenmoses_rating[index]}")

# Determine and display the winner
winner_index = results.ranking.index(0)  # Index of the player with the highest score
winner = players[winner_index]
print(f"\nWinner of the Tournament: {winner.name}")
