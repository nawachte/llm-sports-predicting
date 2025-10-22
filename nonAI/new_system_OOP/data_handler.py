# data_handler.py
import json
import os
import sys
import abc
import re
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
    """
    @abc.abstractmethod
    def fetch_scores(self, start_identifier, end_identifier) -> List[Dict]:
        """
        Abstract method to fetch game scores for a given range.
        """
        pass

    @abc.abstractmethod
    def fetch_lines(self) -> List[Tuple[str, str, float]]:
        """
        Abstract method to fetch betting lines for upcoming games.
        """
        pass

    @abc.abstractmethod
    def get_current_identifier(self) -> int:
        """
        Abstract method to dynamically determine the current week or date for the sport.
        For NFL, this is the week number. For daily sports, a date (YYYYMMDD).
        """
        pass
    
    @abc.abstractmethod
    def get_all_team_names(self) -> List[str]:
        """
        Abstract method to return a list of all team names for the league.
        Needed for initial data seeding.
        """
        pass

# ==============================================================================
# --- Concrete Scraper Implementations ---
# ==============================================================================

class NFLScraper(BaseScraper):
    """
    A concrete implementation of BaseScraper for fetching NFL data from ESPN.
    """
    def get_current_identifier(self) -> int:
        """
        Dynamically determines the most recent NFL week by parsing the
        page's initial state data object.
        """
        start_url = "https://www.espn.com/nfl/scoreboard"
        try:
            response = requests.get(start_url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            match = re.search(r"window\['__espnfitt__'\]\s*=\s*({.*?});", response.text, re.DOTALL)
            if not match:
                print("FATAL: Could not find the '__espnfitt__' data object in the page source.")
                sys.exit(1)
            data = json.loads(match.group(1))
            last_completed_week = data['page']['content']['scoreboard']['season']['type']['week']['number']
            return last_completed_week + 1
        except requests.exceptions.RequestException as e:
            print(f"FATAL: Network error while determining current week: {e}")
            sys.exit(1)
        except (AttributeError, IndexError, ValueError, KeyError) as e:
            print(f"FATAL: Error parsing week number from the page data object: {e}")
            sys.exit(1)

    def get_all_team_names(self) -> List[str]:
        """Returns a list of all NFL team names."""
        # In a production system, this might come from a static file or a reliable API endpoint.
        return [
            "Cardinals", "Falcons", "Ravens", "Bills", "Panthers", "Bears", "Bengals", "Browns",
            "Cowboys", "Broncos", "Lions", "Packers", "Texans", "Colts", "Jaguars", "Chiefs",
            "Raiders", "Chargers", "Rams", "Dolphins", "Vikings", "Patriots", "Saints", "Giants",
            "Jets", "Eagles", "Steelers", "49ers", "Seahawks", "Buccaneers", "Titans", "Commanders"
        ]

    def fetch_scores(self, start_week: int, end_week: int) -> List[Dict]:
        # This function's internal logic remains unchanged from the previous version.
        all_games = []
        YEAR = 2025
        SEASON_TYPE = 2
        for week in range(start_week, end_week + 1):
            url = f"https://www.espn.com/nfl/scoreboard/_/week/{week}/year/{YEAR}/seasontype/{SEASON_TYPE}"
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
                print(f"FATAL: Network error fetching data for week {week}: {e}")
                sys.exit(1)
            except (AttributeError, IndexError, ValueError) as e:
                print(f"FATAL: Error parsing data for week {week}: {e}")
                sys.exit(1)
        return all_games

    def fetch_lines(self) -> List[Tuple[str, str, float]]:
        # This function's internal logic remains unchanged.
        return [("Bengals", "Ravens", 53.0), ("Giants", "Panthers", 41.5), ("Bills", "Colts", 46.0)]


class NBAScraper(BaseScraper):
    """ A concrete implementation for NBA data to demonstrate extensibility. """
    def get_current_identifier(self) -> int:
        """ Returns today's date as an integer in YYYYMMDD format. """
        return int(date.today().strftime('%Y%m%d'))

    def get_all_team_names(self) -> List[str]:
        """ Returns a placeholder list of NBA team names. """
        return ["Lakers", "Clippers", "Nets", "Knicks"] # Placeholder

    def fetch_scores(self, start_date: int, end_date: int) -> List[Dict]:
        # Placeholder implementation for fetching daily scores.
        print(f"INFO: Fetching NBA scores from {start_date} to {end_date} would happen here.")
        return []

    def fetch_lines(self) -> List[Tuple[str, str, float]]:
        # Placeholder implementation for fetching lines.
        return [("Lakers", "Clippers", 220.5)]

# ==============================================================================
# --- DataHandler ---
# ==============================================================================

class DataHandler:
    """
    Orchestrates data loading, updating, analysis, and saving for a specific sport.
    """
    def __init__(self, sport_key: str, state_file: str):
        self.sport_key = sport_key
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
        return teams, metadata

    def _save_state(self, teams: Dict[str, Team], metadata: Dict) -> None:
        """Saves the current state of teams and metadata to the JSON file."""
        serializable_teams = {name: team.__dict__ for name, team in teams.items()}
        state = {'metadata': metadata, 'teams': serializable_teams}
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=4)

    def _update_scores(self, teams: Dict[str, Team], metadata: Dict, scraper: BaseScraper) -> Tuple[Dict[str, Team], Dict]:
        """
        Handles both initial data seeding and incremental updates.
        """
        is_weekly = (self.sport_key == 'nfl')
        
        # --- INITIAL SEEDING LOGIC ---
        if not teams:
            team_names = scraper.get_all_team_names()
            teams = {name: Team(name) for name in team_names}
            last_updated = 0 # Start from the beginning of the season.
        else:
            if is_weekly:
                last_updated = metadata.get(f'last_updated_{self.sport_key}_week', 0)
            else:
                # Default to yesterday if no date is found for daily sports.
                yesterday = date.today() - timedelta(days=1)
                last_updated = metadata.get(f'last_updated_{self.sport_key}_date', int(yesterday.strftime('%Y%m%d')))

        # --- IDENTIFIER CALCULATION LOGIC ---
        current_identifier = scraper.get_current_identifier()

        if is_weekly:
            metadata_key = f'last_updated_{self.sport_key}_week'
            start_identifier = last_updated + 1
            end_identifier = current_identifier - 1
        else: # Daily sports
            metadata_key = f'last_updated_{self.sport_key}_date'
            end_identifier = current_identifier - 1 # Scores up to yesterday.
            last_updated_dt = datetime.strptime(str(last_updated), '%Y%m%d').date()
            start_identifier = int((last_updated_dt + timedelta(days=1)).strftime('%Y%m%d'))
        
        if start_identifier > end_identifier:
            return teams, metadata

        game_scores = scraper.fetch_scores(start_identifier, end_identifier)

        for game in game_scores:
            t1_name, t2_name = game['team1_name'], game['team2_name']
            t1_score, t2_score = game['team1_score'], game['team2_score']
            if t1_name in teams and t2_name in teams:
                teams[t1_name].add_game_result(t1_score, t2_score)
                teams[t2_name].add_game_result(t2_score, t1_score)
        
        metadata[metadata_key] = end_identifier
        return teams, metadata

    def run_analysis(self, scraper: BaseScraper) -> None:
        """
        Main orchestrator. Loads state, updates data, runs analysis, and saves.
        """
        teams, metadata = self._load_state()
        
        teams, metadata = self._update_scores(teams, metadata, scraper)
        
        lines = scraper.fetch_lines()
        if not lines:
            print(f"WARNING: Could not fetch betting lines for {self.sport_key.upper()}.")
            return

        matchups = []
        for t1_name, t2_name, line in lines:
            if t1_name in teams and t2_name in teams:
                matchup = Matchup(teams[t1_name], teams[t2_name], line)
                matchup.run_projections()
                matchups.append(matchup)

        matchups.sort(key=lambda m: abs(m.get_ou_score()), reverse=True)
        
        print(f"\n--- {self.sport_key.upper()} Over/Under Projections ---")
        for matchup in matchups:
            team1, team2 = matchup.team1.name, matchup.team2.name
            score, line_val = matchup.get_ou_score(), matchup.over_under_line
            print(f"{team1} vs {team2} (Line: {line_val}): O/U Score = {score}")

        self._save_state(teams, metadata)

# ==============================================================================
# --- Example Usage ---
# ==============================================================================
if __name__ == '__main__':
    # --- To analyze NFL ---
    # 1. Instantiate the handler for the desired sport.
    nfl_handler = DataHandler(sport_key='nfl', state_file='nfl_data_state.json')
    # 2. Instantiate the corresponding scraper.
    nfl_scraper = NFLScraper()
    # 3. Run the analysis.
    # nfl_handler.run_analysis(scraper=nfl_scraper)
    
    print("\nExample usage block executed. To run, uncomment the handler.run_analysis() line.")