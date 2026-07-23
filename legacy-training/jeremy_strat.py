import tkinter as tk
from tkinter import ttk, messagebox
import axelrod as axl
import sqlite3

# Define the Jeremy strategy
class Jeremy(axl.Player):
    name = "Jeremy"

    def __init__(self):
        super().__init__()
        self.defections_count = 0
        self.defect_forever = False
        self.first_move = True

    def strategy(self, opponent):
        if self.first_move:
            self.first_move = False
            return axl.Action.D
        if self.defect_forever:
            return axl.Action.D
        if opponent.history[-1:] == [axl.Action.D]:
            self.defections_count += 1
        if self.defections_count >= 3:
            self.defect_forever = True
            return axl.Action.D
        return axl.Action.C

# Create a connection to the SQLite database
def create_connection():
    conn = sqlite3.connect('axelrod_tournament.db')
    return conn

# Create the matches table in the database
def create_table():
    conn = create_connection()
    cursor = conn.cursor()
    table_query = """
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        opponent TEXT NOT NULL,
        score TEXT NOT NULL,
        winner TEXT NOT NULL
    );
    """
    cursor.execute(table_query)
    conn.commit()
    conn.close()

create_table()

# Function to insert match results into the database
def log_match(opponent_name, score, winner):
    conn = create_connection()
    cursor = conn.cursor()
    insert_query = """
    INSERT INTO matches (opponent, score, winner)
    VALUES (?, ?, ?);
    """
    cursor.execute(insert_query, (opponent_name, score, winner))
    conn.commit()
    conn.close()

# Function to run the match
def run_match():
    opponent_class = basic_strategies[opponent_var.get()]
    opponent = opponent_class()

    player1 = Jeremy()
    player2 = opponent

    match = axl.Match([player1, player2], turns=10)
    results = match.play()

    scores = match.final_score()
    winner_name = "Draw"
    if scores[0] > scores[1]:
        winner_name = "Jeremy"
        result_text = f'Winner is Jeremy with a score of {scores[0]}'
    elif scores[0] < scores[1]:
        winner_name = opponent.name
        result_text = f'Winner is {opponent.name} with a score of {scores[1]}'
    else:
        result_text = 'The match is a draw.'

    log_match(opponent.name, f'{scores[0]} - {scores[1]}', winner_name)
    messagebox.showinfo("Match Result", result_text)

# Create the GUI
app = tk.Tk()
app.title("Axelrod Tournament Simulation")

# Dropdown menu setup
basic_strategies = {strat.name: strat for strat in axl.basic_strategies}
basic_strategies.update({
    axl.Random().name: axl.Random,
    axl.Bully().name: axl.Bully
})

opponent_var = tk.StringVar()
opponent_combo = ttk.Combobox(app, textvariable=opponent_var, values=list(basic_strategies.keys()))
opponent_combo.grid(column=0, row=0, padx=10, pady=10)

run_button = ttk.Button(app, text="Run Match", command=run_match)
run_button.grid(column=0, row=1, padx=10, pady=10)

app.mainloop()
