# Quantum Minesweeper

## Installation
Create an environment with conda with
> conda env create

The default name is `qminesweeper`.

## Running Quantum Minesweeper
You can run the textual interface with

> conda activate qminesweep
> 
> python ./src/qms-tui.py

For the web interface
> conda activate qminesweep
>
> bash ./flask-webapp.py

and then open `http://127.0.0.1:5000` on the broswer.

## Ideas for the future:
- New move: draw a line on the board and return the bipartite entanglement. Can a player get advantage of this?
- Select the basis for the clue: X, Y
- 