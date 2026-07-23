import axelrod as axl
import sqlite3
import datetime

def setup_database():
    conn = sqlite3.connect('tournament_results.db')
    c = conn.cursor()
    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS results
                 (timestamp TEXT, strategy_name TEXT, rounds_played INTEGER, placement INTEGER)''')
    conn.commit()
    conn.close()

def insert_result(timestamp, strategy_name, rounds_played, placement):
    conn = sqlite3.connect('tournament_results.db')
    c = conn.cursor()
    c.execute("INSERT INTO results (timestamp, strategy_name, rounds_played, placement) VALUES (?, ?, ?, ?)",
              (timestamp, strategy_name, rounds_played, placement))
    conn.commit()
    conn.close()

# Setup database
setup_database()

# Define selected strategies
selected_strategies = [
    axl.Alternator(),
    axl.AntiTitForTat(),
    axl.Bully(),
    axl.Cooperator(),
        axl.SuspiciousTitForTat(),
    axl.TitForTat(),
    axl.WinShiftLoseStay(),
    axl.WinStayLoseShift()
]

# Define the number of rounds for the tournament
num_rounds = 1

# Initialize a dictionary to keep track of each player's total score
total_scores = {strategy.name: 0 for strategy in selected_strategies}

# Run the tournament for each pair of players
for i, player1 in enumerate(selected_strategies):
    for j, player2 in enumerate(selected_strategies):
        if j > i:
            tournament = axl.Tournament([player1, player2], turns=num_rounds, repetitions=1)
            results = tournament.play()
            total_scores[player1.name] += results.scores[0][0]
            total_scores[player2.name] += results.scores[1][0]

# Sort the total_scores dictionary by score in descending order
sorted_scores = sorted(total_scores.items(), key=lambda item: item[1], reverse=True)

# Get the current timestamp
current_timestamp = datetime.datetime.now().isoformat()

# Insert the top three results into the database
for index, (name, score) in enumerate(sorted_scores[:3]):
    insert_result(current_timestamp, name, num_rounds, index + 1)

# Display the top three winners
print("Top Three Winners:")
for index, (name, score) in enumerate(sorted_scores[:3]):
    print(f"{index + 1}. {name} with a total score of {score}")
