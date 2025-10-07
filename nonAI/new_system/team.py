# team.py
from typing import List, Optional
import statistics

class Team:
    """
    Represents a single NFL team and its performance statistics.
    
    This class encapsulates all data related to a team, such as points
    scored and allowed, and provides methods to calculate statistical averages.
    """
    def __init__(self, name: str):
        """
        Initializes a Team object.

        Args:
            name (str): The name of the team (e.g., "Cardinals").
        """
        self.name: str = name
        self.scores_for: List[int] = []
        self.scores_against: List[int] = []

    def __repr__(self) -> str:
        return f"Team({self.name})"

    def add_game_result(self, scored: int, allowed: int) -> None:
        """
        Adds the result of a single game to the team's history.

        Args:
            scored (int): Points the team scored in the game.
            allowed (int): Points the team allowed in the game.
        """
        self.scores_for.append(scored)
        self.scores_against.append(allowed)

    def average_points_scored(self, last_n_games: Optional[int] = None) -> float:
        """
        Calculates the average points scored by the team.

        Args:
            last_n_games (Optional[int]): If provided, calculates the average
                over the last 'n' games. Otherwise, calculates the season average.

        Returns:
            float: The average points scored. Returns 0.0 if no games are available.
        """
        scores = self.scores_for[-last_n_games:] if last_n_games else self.scores_for
        if not scores:
            return 0.0
        return statistics.mean(scores)

    def average_points_allowed(self, last_n_games: Optional[int] = None) -> float:
        """
        Calculates the average points allowed by the team.

        Args:
            last_n_games (Optional[int]): If provided, calculates the average
                over the last 'n' games. Otherwise, calculates the season average.

        Returns:
            float: The average points allowed. Returns 0.0 if no games are available.
        """
        scores = self.scores_against[-last_n_games:] if last_n_games else self.scores_against
        if not scores:
            return 0.0
        return statistics.mean(scores)