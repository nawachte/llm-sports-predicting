# matchup.py
from team import Team
import statistics

class Matchup:
    """
    Represents a single game matchup between two teams.

    This class contains the analytical logic to generate six different
    projected point totals and aggregate them into a final betting score.
    """
    def __init__(self, team1: Team, team2: Team, over_under_line: float):
        """
        Initializes a Matchup object.

        Args:
            team1 (Team): The first Team object in the matchup.
            team2 (Team): The second Team object in the matchup.
            over_under_line (float): The official betting line for the game.
        """
        self.team1: Team = team1
        self.team2: Team = team2
        self.over_under_line: float = over_under_line
        self.projections: dict = {}

    def __repr__(self) -> str:
        """Provides a formal string representation of the Matchup object."""
        return f"Matchup({self.team1.name} vs {self.team2.name})"

    def _calc_avg_combined_pf(self, last_n=None) -> float:
        """Test 1 & 3: Avg Team1 Scored + Avg Team2 Scored."""
        t1_pf = self.team1.average_points_scored(last_n)
        t2_pf = self.team2.average_points_scored(last_n)
        return t1_pf + t2_pf

    def _calc_avg_combined_pa(self, last_n=None) -> float:
        """Test 2 & 4: Avg Team1 Allowed + Avg Team2 Allowed."""
        t1_pa = self.team1.average_points_allowed(last_n)
        t2_pa = self.team2.average_points_allowed(last_n)
        return t1_pa + t2_pa

    def _calc_adjusted_total(self, last_n=None) -> float:
        """Test 5 & 6: Adjusted total based on offense vs. defense."""
        t1_pf = self.team1.average_points_scored(last_n)
        t2_pf = self.team2.average_points_scored(last_n)
        t1_pa = self.team1.average_points_allowed(last_n)
        t2_pa = self.team2.average_points_allowed(last_n)
        
        adj1 = statistics.mean([t1_pf, t2_pa])
        adj2 = statistics.mean([t2_pf, t1_pa])
        return adj1 + adj2

    def run_projections(self) -> None:
        """
        Executes all six projection calculations and stores them.
        """
        self.projections['avg_pf_season'] = self._calc_avg_combined_pf()
        self.projections['avg_pa_season'] = self._calc_avg_combined_pa()
        self.projections['avg_pf_last_3'] = self._calc_avg_combined_pf(last_n=3)
        self.projections['avg_pa_last_3'] = self._calc_avg_combined_pa(last_n=3)
        self.projections['adj_total_season'] = self._calc_adjusted_total()
        self.projections['adj_total_last_3'] = self._calc_adjusted_total(last_n=3)

    def get_ou_score(self) -> int:
        """
        Calculates the aggregate over/under score.

        Each projection is compared to the betting line, assigned a value of
        +1 (over), -1 (under), or 0 (push), and then summed.

        Returns:
            int: The final "o/u score".
        """
        if not self.projections:
            self.run_projections()
            
        score = 0
        for proj in self.projections.values():
            if proj > self.over_under_line:
                score += 1
            elif proj < self.over_under_line:
                score -= 1
        return score