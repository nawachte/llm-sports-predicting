# data_handler.py
import json
import os
import sys
import abc
from typing import Dict, List, Tuple
from datetime import date, timedelta, datetime

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
    def fetch_scores(self, start_identifier, end_identifier) -> List[Dict]:
        """
        Abstract method to fetch game scores for a given range.
        For NFL, identifiers are week numbers. For NBA/NHL, they are dates (YYYYMMDD).

        Args:
            start_identifier: The starting point (e.g., week number, date as YYYYMMDD).
            end_identifier: The ending point.

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
# --- Concrete Scraper Implementations ---
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
        YEAR = 2025
        SEASON_TYPE = 2

        for week in range(start_week, end_week + 1):
            url = f"https://www.espn.com/nfl/scoreboard/_/week/{week}/year/{YEAR}/seasontype/{SEASON_TYPE}"
            print(f"Fetching NFL scores from: {url}")
            
            try:
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                scoreboards = soup.find_all('div', class_='scoreboard-wrapper')

                for board in scoreboards:
                    teams = board.find_all('span', class_='sb-team-short')
                    scores = board.find_all('div', class_='score')
                    if len(teams) == 2 and len(scores) >= 2:
                        all_games.append({
                            'team1_name': teams[0].text.strip(), 'team2_name': teams[1].text.strip(),
                            'team1_score': int(scores[0].text.strip()), 'team2_score': int(scores[1].text.strip())
                        })
            except requests.exceptions.RequestException as e:
                print(f"Error fetching data for week {week}: {e}")
            except (AttributeError, IndexError, ValueError) as e:
                print(f"Error parsing data for week {week}: {e}")
        return all_games

    def fetch_lines(self) -> List[Tuple[str, str, float]]:
        """
        Fetches the betting lines for the upcoming NFL week.
        *** Placeholder Implementation ***
        """
        print("Fetching NFL betting lines...")
        return [("Bengals", "Ravens", 53.0), ("Giants", "Panthers", 41.5), ("Bills", "Colts", 46.0)]


class NBAScraper(BaseScraper):
    """
    A concrete implementation of BaseScraper for fetching NBA data from ESPN.
    """
    def fetch_scores(self, start_date: int, end_date: int) -> List[Dict]:
        """
        Scrapes ESPN for NBA scores for a specified range of dates.

        Args:
            start_date (int): The first date to fetch (format YYYYMMDD).
            end_date (int): The last date to fetch (format YYYYMMDD).

        Returns:
            List[Dict]: A list of game result dictionaries.
        """
        all_games = []
        start_dt = datetime.strptime(str(start_date), '%Y%m%d').date()
        end_dt = datetime.strptime(str(end_date), '%Y%m%d').date()
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y%m%d')
            url = f"https://www.espn.com/nba/scoreboard/_/date/{date_str}"
            print(f"Fetching NBA scores from: {url}")
            try:
                # NOTE: Scraping logic is assumed to be similar to NFL's for this example.
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                scoreboards = soup.find_all('div', class_='scoreboard-wrapper')
                for board in scoreboards:
                    teams = board.find_all('span', class_='sb-team-short')
                    scores = board.find_all('div', class_='score')
                    if len(teams) == 2 and len(scores) >= 2:
                        all_games.append({
                            'team1_name': teams[0].text.strip(), 'team2_name': teams[1].text.strip(),
                            'team1_score': int(scores[0].text.strip()), 'team2_score': int(scores[1].text.strip())
                        })
            except requests.exceptions.RequestException as e:
                print(f"Error fetching data for date {date_str}: {e}")
            except (AttributeError, IndexError, ValueError) as e:
                print(f"Error parsing data for date {date_str}: {e}")
            current_dt += timedelta(days=1)
        return all_games

    def fetch_lines(self) -> List[Tuple[str, str, float]]:
        """
        Fetches the betting lines for upcoming NBA games.
        *** Placeholder Implementation ***
        """
        print("Fetching NBA betting lines...")
        return [("Lakers", "Clippers", 220.5), ("Nets", "Knicks", 215.0)]


# ==============================================================================
# --- DataHandler ---
# ==============================================================================

class DataHandler:
    """
    Orchestrates data loading, updating, analysis, and saving.
    This class is now sport-agnostic and relies on a scraper object.
    """
    def __init__(self, scraper: BaseScraper, state_file: str):
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
        state = {'metadata': metadata, 'teams': serializable_teams}
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=4)
        print(f"Saved state to {self.state_file}")

    def _get_current_nfl_week(self) -> int:
        """
        Dynamically determines the most recent NFL week by parsing the
        page's initial state data object, rather than scraping rendered HTML.

        This method fetches the main scoreboard page and uses regular expressions
        to find and extract the '__espnfitt__' JSON object. This object contains
        the definitive data for the current week, providing a more reliable source
        than CSS classes which may be rendered dynamically.

        Returns:
            int: The week number for which to generate predictions. Returns a
                 default of 1 if the process fails.
        """
        import re
        import json

        start_url = "https://www.espn.com/nfl/scoreboard"

        try:
            response = requests.get(start_url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()

            # Use a regular expression to find the window['__espnfitt__'] object in the script tags.
            # The re.DOTALL flag allows the '.' to match newlines, as the JSON object is multi-line.
            match = re.search(r"window\['__espnfitt__'\]\s*=\s*({.*?});", response.text, re.DOTALL)

            if not match:
                print("Warning: Could not find the '__espnfitt__' data object in the page source.")
                sys.exit()

            # The JSON data is the first captured group from our regex.
            json_data_string = match.group(1)
            
            # Parse the captured string into a Python dictionary.
            data = json.loads(json_data_string)

            # Navigate through the nested dictionary to find the current week number.
            # This path is specific to the structure of the '__espnfitt__' object.
            last_completed_week = data['page']['content']['scoreboard']['season']['type']['week']['number']
            
            # The analysis is for the *next* week.
            prediction_week = last_completed_week + 1
            
            return prediction_week

        except requests.exceptions.RequestException as e:
            print(f"Warning: Network error while determining current week: {e}")
            sys.exit()
        except (AttributeError, IndexError, ValueError, KeyError) as e:
            # This will catch errors from regex, JSON parsing, or incorrect key paths.
            print(f"Warning: Error parsing week number from the page data object: {e}")
            sys.exit()

    def _update_scores(self, teams: Dict[str, Team], metadata: Dict, sport_key: str) -> Tuple[Dict[str, Team], Dict]:
        """
        Efficiently updates scores by fetching only the missing weeks or dates.
        """
        # Determine if the sport is updated weekly (NFL) or daily (NBA, etc.)
        if sport_key == 'nfl':
            metadata_key = f'last_updated_{sport_key}_week'
            current_identifier = self._get_current_nfl_week()
            last_updated = metadata.get(metadata_key, 0)
            
            start_identifier = last_updated + 1
            end_identifier = current_identifier - 1 # Fetch scores up to the week before the current one.
        else: # Daily sports
            metadata_key = f'last_updated_{sport_key}_date'
            yesterday = date.today() - timedelta(days=1)
            end_identifier = int(yesterday.strftime('%Y%m%d'))
            
            # If no history, start fetching from a reasonable point, e.g., 7 days ago.
            if not metadata.get(metadata_key):
                seven_days_ago = yesterday - timedelta(days=7)
                last_updated = int(seven_days_ago.strftime('%Y%m%d'))
            else:
                last_updated = metadata.get(metadata_key)

            last_updated_dt = datetime.strptime(str(last_updated), '%Y%m%d').date()
            start_identifier = int((last_updated_dt + timedelta(days=1)).strftime('%Y%m%d'))

        if start_identifier > end_identifier:
            print(f"{sport_key.upper()} data is already up to date.")
            return teams, metadata

        print(f"Updating {sport_key.upper()} scores from {start_identifier} to {end_identifier}...")
        game_scores = self.scraper.fetch_scores(start_identifier, end_identifier)

        for game in game_scores:
            t1_name, t2_name = game['team1_name'], game['team2_name']
            t1_score, t2_score = game['team1_score'], game['team2_score']
            if t1_name in teams and t2_name in teams:
                teams[t1_name].add_game_result(t1_score, t2_score)
                teams[t2_name].add_game_result(t2_score, t1_score)
        
        metadata[metadata_key] = end_identifier
        return teams, metadata

    def run_analysis(self, sport_key: str) -> None:
        """
        Main orchestrator. Loads state, updates data, runs analysis, and saves.
        This function is now intelligent, requiring no date/week parameter.
        
        Args:
            sport_key (str): A key to identify the sport ('nfl', 'nba', etc.).
        """
        teams, metadata = self._load_state()
        
        if not teams:
            print("No existing state file found. Please initialize team data first.")
            return

        # Update scores to be current based on the last saved state
        teams, metadata = self._update_scores(teams, metadata, sport_key)
        
        # Fetch lines for the upcoming games
        lines = self.scraper.fetch_lines()
        if not lines:
            print(f"Could not fetch betting lines for {sport_key.upper()}.")
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
        
        print(f"\n--- {sport_key.upper()} Over/Under Projections ---")
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
    # This block demonstrates how you would use these classes from a notebook.

    # --- To analyze NFL ---
    # 1. Instantiate the NFL scraper
    nfl_scraper = NFLScraper()
    # 2. Instantiate the DataHandler
    nfl_handler = DataHandler(scraper=nfl_scraper, state_file='nfl_data_state.json')
    # 3. Run the analysis. It will automatically determine the weeks to update.
    # nfl_handler.run_analysis(sport_key='nfl')

    # --- To analyze NBA ---
    # 1. Instantiate the NBA scraper
    nba_scraper = NBAScraper()
    # 2. Instantiate the DataHandler
    nba_handler = DataHandler(scraper=nba_scraper, state_file='nba_data_state.json')
    # 3. Run the analysis. It will automatically determine the dates to update.
    # nba_handler.run_analysis(sport_key='nba')
    
    print("\nExample usage block executed. To run a full analysis,")
    print("ensure a state file exists and uncomment the handler.run_analysis() lines.")