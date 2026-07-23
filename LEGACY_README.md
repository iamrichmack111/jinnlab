

---

# Moran Process Simulation

This Python program simulates a Moran Process between two players using strategies from the Axelrod library. It allows you to select two players and run a simulation to determine the winner based on the Moran Process dynamics. Additionally, it stores the simulation results in a SQLite database, including the seed used and the timestamp of the simulation.

## Prerequisites

- Python 3.x
- Axelrod library (`pip install axelrod`)

## Installation

1. Clone the repository to your local machine:

```
git clone https://github.com/your-username/game-theory-jinn.git
```

2. Navigate to the project directory:

```
cd moran-process-simulation
```

3. Install the required Python packages:

```
pip install -r requirements.txt
```

## Usage

1. Run the program:

```
python game-theory.py
```

2. The program will open a GUI window where you can select two players from the dropdown menus.

3. Click on the "Start Simulation" button to run the Moran Process simulation.

4. A message box will pop up displaying the winner of the simulation.

5. The simulation results are stored in a SQLite database named `results.db` in the project directory.

## Customization

- **Changing Seed**: You can modify the seed used for the simulation by changing the `seed` variable in the `start_simulation` method of the `MoranProcessGUI` class.

## SQLite Database Schema

The SQLite database `results.db` contains a single table named `results` with the following schema:

- `id`: Primary key (auto-incrementing integer)
- `player1`: Name of the first player
- `player2`: Name of the second player
- `winner`: Name of the winner (or "Tie" if it's a tie)
- `seed`: Seed used for the simulation
- `timestamp`: Timestamp of the simulation

## Credits

- This program utilizes the Axelrod library for simulating the Moran Process.
- Created by Nicholas Franklin

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.

---

Feel free to customize this README according to your specific project details and requirements!