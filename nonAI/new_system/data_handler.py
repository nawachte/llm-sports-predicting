# data_handler.py
import json
import os
import abc
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

from team import Team
from matchup import Matchup

# ==============================================================================
# --- Abstract Base Scraper ---
# ==============================================================================

class BaseScraper(abc.ABC):
    """
    Abstract base class defining the interface for all sport-specific scrapers.
    Ensures that any scraper created will have the necessary methods to interact
    with the DataHandler.
    """
    @abc.abstractmethod
    def fetch_scores(self, start_identifier: int, end_identifier: int) -> List[Dict]:
        """
        Abstract method to fetch game scores for a given range.

        Args:
            start_identifier (int): The starting point (e.g., week number, date).
            end_identifier (int): The ending point.

        Returns:
            A list of dictionaries, each representing a game's result.
            Example: [{'team1_name': ..., 'team2_name': ..., 'team1_score': ..., 'team2_score': ...}]
        """
        pass

    @abc.abstractmethod
    def fetch_lines(self) -> List[Tuple[str, str, float]]:
        """
        Abstract method to fetch betting lines for upcoming games.

        Returns:
            A list of tuples, each representing a matchup and its line.
            Example: [('TeamA', 'TeamB', 45.5), ...]
        """
        pass

# ==============================================================================
# --- Concrete NFL Scraper ---
# ==============================================================================

class NFLScraper(BaseScraper):
    """
    A concrete implementation of BaseScraper for fetching NFL data from ESPN.
    """
    def fetch_scores(self, start_week: int, end_week: int) -> List[Dict]:
        """
        Scrapes ESPN for NFL scores for a specified range of weeks.

        Args:
            start_week (int): The first week to fetch scores for.
            end_week (int): The last week to fetch scores for.

        Returns:
            List[Dict]: A list of game result dictionaries.
        """
        all_games = []
        YEAR = 2025  # As specified in the notebook
        SEASON_TYPE = 2

        for week in range(start_week, end_week + 1):
            url = f"https://www.espn.com/nfl/scoreboard/_/week/{week}/year/{YEAR}/seasontype/{SEASON_TYPE}"
            print(f"Fetching scores from: {url}")
            
            try:
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all game containers on the page
                scoreboards = soup.find_all('div', class_='scoreboard-wrapper')

                for board in scoreboards:
                    # Find team names and scores within each container
                    teams = board.find_all('span', class_='sb-team-short')
                    scores = board.find_all('div', class_='score')
                    
                    # Ensure we have a complete game with two teams and two scores
                    if len(teams) == 2 and len(scores) >= 2:
                        team1_name = teams[0].text.strip()
                        team2_name = teams[1].text.strip()
                        team1_score = int(scores[0].text.strip())
                        team2_score = int(scores[1].text.strip())
                        
                        game_data = {
                            'team1_name': team1_name,
                            'team2_name': team2_name,
                            'team1_score': team1_score,
                            'team2_score': team2_score
                        }
                        all_games.append(game_data)

            except requests.exceptions.RequestException as e:
                print(f"Error fetching data for week {week}: {e}")
            except (AttributeError, IndexError, ValueError) as e:
                print(f"Error parsing data for week {week}: {e}")

        return all_games

    def fetch_lines(self) -> List[Tuple[str, str, float]]:
        """
        Fetches the betting lines for the upcoming NFL week.

        *** Placeholder Implementation ***
        This method should be updated to scrape a reliable source for betting odds.
        """
        print("Fetching betting lines...")
        # This is placeholder data for demonstration.
        return [
            ("Bengals", "Ravens", 53.0),
            ("Giants", "Panthers", 41.5),
            ("Bills", "Colts", 46.0),
            # ... Add all other matchups and lines for the week here
        ]

# ==============================================================================
# --- Refactored DataHandler ---
# ==============================================================================

class DataHandler:
    """
    Orchestrates data loading, updating, analysis, and saving.
    This class is now sport-agnostic and relies on a scraper object.
    """
    def __init__(self, scraper: BaseScraper, state_file: str = 'nfl_data_state.json'):
        self.scraper = scraper
        self.state_file = state_file

    def _load_state(self) -> Tuple[Dict[str, Team], Dict]:
        """Loads both team data and metadata from the JSON state file."""
        if not os.path.exists(self.state_file):
            return {}, {}
            
        with open(self.state_file, 'r') as f:
            state = json.load(f)
            
        team_data = state.get('teams', {})
        metadata = state.get('metadata', {})
        
        teams = {}
        for name, data in team_data.items():
            team = Team(name)
            team.scores_for = data['scores_for']
            team.scores_against = data['scores_against']
            teams[name] = team
            
        print(f"Loaded state for {len(teams)} teams from {self.state_file}")
        return teams, metadata

    def _save_state(self, teams: Dict[str, Team], metadata: Dict) -> None:
        """Saves the current state of teams and metadata to the JSON file."""
        serializable_teams = {name: team.__dict__ for name, team in teams.items()}
        state = {
            'metadata': metadata,
            'teams': serializable_teams
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=4)
        print(f"Saved state to {self.state_file}")

    def _update_scores(self, teams: Dict[str, Team], metadata: Dict, current_week: int, sport_key: str) -> Tuple[Dict[str, Team], Dict]:
        """
        Efficiently updates scores by fetching only the weeks that are missing.
        """
        last_updated = metadata.get(f'last_updated_{sport_key}', 0)
        start_week_to_fetch = last_updated + 1
        end_week_to_fetch = current_week - 1

        if start_week_to_fetch > end_week_to_fetch:
            print("Team data is already up to date.")
            return teams, metadata

        print(f"Updating scores from week {start_week_to_fetch} to {end_week_to_fetch}...")
        weekly_scores = self.scraper.fetch_scores(start_week_to_fetch, end_week_to_fetch)

        for game in weekly_scores:
            t1_name, t2_name = game['team1_name'], game['team2_name']
            t1_score, t2_score = game['team1_score'], game['team2_score']

            if t1_name in teams and t2_name in teams:
                teams[t1_name].add_game_result(t1_score, t2_score)
                teams[t2_name].add_game_result(t2_score, t1_score)
        
        metadata[f'last_updated_{sport_key}'] = end_week_to_fetch
        return teams, metadata

    def run_analysis_for_week(self, current_week: int, sport_key: str = 'nfl') -> None:
        """
        The main orchestrator function. Loads state, updates data, runs analysis,
        and saves the new state. This is the primary function to be called.
        
        Args:
            current_week (int): The current NFL week number (e.g., for week 7 predictions, this is 7).
            sport_key (str): A key to identify the sport in the metadata.
        """
        teams, metadata = self._load_state()
        
        # If teams are not loaded, we need to initialize them.
        # A full implementation would fetch all historical data or require a seed file.
        if not teams:
            print("No existing state file found. Please initialize team data first.")
            # For now, we will exit if the state is not pre-populated.
            return

        # Update with scores from previous weeks if needed
        teams, metadata = self._update_scores(teams, metadata, current_week, sport_key + '_week')
        
        # Fetch lines for the current week's games
        lines = self.scraper.fetch_lines()
        if not lines:
            print(f"Could not fetch betting lines for week {current_week}.")
            return

        # Create Matchup objects and run projections
        matchups = []
        for t1_name, t2_name, line in lines:
            if t1_name in teams and t2_name in teams:
                matchup = Matchup(teams[t1_name], teams[t2_name], line)
                matchup.run_projections()
                matchups.append(matchup)

        # Sort and display results
        matchups.sort(key=lambda m: abs(m.get_ou_score()), reverse=True)
        
        print("\n--- Weekly Over/Under Projections ---")
        for matchup in matchups:
            team1 = matchup.team1.name
            team2 = matchup.team2.name
            score = matchup.get_ou_score()
            line = matchup.over_under_line
            print(f"{team1} vs {team2} (Line: {line}): O/U Score = {score}")

        # Save the updated state
        self._save_state(teams, metadata)

# ==============================================================================
# --- Example Usage ---
# ==============================================================================
if __name__ == '__main__':
    # This block demonstrates how you would use these classes.
    # In your project, you would import and run this from your main notebook.

    # 1. Instantiate the specific scraper for the sport you want.
    nfl_scraper = NFLScraper()

    # 2. Instantiate the DataHandler with the chosen scraper.
    handler = DataHandler(scraper=nfl_scraper, state_file='nfl_data_state.json')

    # 3. To run the analysis for the upcoming week (e.g., Week 7), call this single function.
    #    It will handle loading, catching up on past scores, fetching new lines,
    #    running the analysis, and saving the new state.
    #    **NOTE:** This requires a 'nfl_data_state.json' file with initial team data to exist.
    
    # handler.run_analysis_for_week(current_week=7)
    
    print("\nExample usage block executed. To run a full analysis,")
    print("ensure 'nfl_data_state.json' is populated with initial team data and uncomment the line above.")