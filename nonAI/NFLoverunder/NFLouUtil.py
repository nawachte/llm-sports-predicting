# NFLouUtil.py

import requests
import os
import json
from typing import Dict, List, Tuple, Any
from urllib.parse import urlparse

CORE_WEEK_EVENTS = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/types/2/weeks/{week}/events"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
JSON_FILE = "NFLscores.json"

def _get(url: str, **params):
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def _event_ids_for_week(year: int, week: int) -> List[str]:
    """Return list of numeric event IDs for a given season week."""
    ids: List[str] = []
    url = CORE_WEEK_EVENTS.format(year=year, week=week)
    params = {"limit": 300}
    while True:
        data = _get(url, **params)
        for it in data.get("items", []):
            ref = it.get("$ref")
            if not ref:
                continue
            # Parse ".../events/{id}?lang=en&region=us"
            p = urlparse(ref)
            eid = p.path.rstrip("/").split("/")[-1]  # numeric id only
            if eid.isdigit():
                ids.append(eid)
        next_url = (data.get("page") or {}).get("next")
        if not next_url:
            break
        url, params = next_url, {}  # 'next' already includes query
    return ids

def _summary_by_event_id(event_id: str) -> dict:
    return _get(SUMMARY_URL, event=event_id)

def _load_json():
    if not os.path.exists(JSON_FILE):
        return {"metadata": {"most_recent_week": 0}, "scored": {}, "allowed": {}}
    with open(JSON_FILE, 'r') as f:
        return json.load(f)

def _save_json(data):
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def scrape_points_test(scored,allowed,num_games,manual_check=True):
    ''' Run tests on scraped scored and allowed data '''

    # assert each team has same number of games scored and allowed
    for team in scored:
        assert len(scored[team]) == num_games, f"Team {team} has {len(scored[team])} games instead of the expected {num_games}."
        assert len(allowed[team]) == num_games, f"Team {team} has {len(allowed[team])} games instead of the expected {num_games}."

    # assert scored and allowed are permutations of each other
    scored_list = []
    allowed_list = []
    for team in scored:
        scored_list.extend(scored[team])
        allowed_list.extend(allowed[team])
    def _sort_key(x):
        try:
            return (0, int(float(x)))
        except Exception:
            return (1, str(x))
    scored_list.sort(key=_sort_key)
    allowed_list.sort(key=_sort_key)
    assert scored_list == allowed_list, "Scored and Allowed points are not permutations of each other"
   
    # manual spot check
    if manual_check:
        print("Manual check of random games:")
        import random
        teams = list(scored.keys())
        for _ in range(10):
            week = random.randint(0, num_games-1)
            chosen_team = random.choice(teams)
            print(f"Week {week + 1}, Team: {chosen_team}, Scored: {scored[chosen_team][week]}, Allowed: {allowed[chosen_team][week]}")

def scrape_points_by_team(start_week: int, end_week: int, season_year: int = 2025):
    if end_week < start_week:
        raise ValueError("end_week must be greater than or equal to start_week")
    
    # -----------------------------------------------------------------
    # STEP 1: Scrape all completed games in range into a flat list
    # -----------------------------------------------------------------
    rows = []
    for wk in range(start_week, end_week + 1):
        for eid in _event_ids_for_week(season_year, wk):
            summ = _summary_by_event_id(eid)
            comp = ((summ.get("header") or {}).get("competitions") or [{}])[0]
            status = comp.get("status", {})
            if not ((status.get("type") or {}).get("completed") is True):
                continue
            comps = comp.get("competitors", [])
            if len(comps) < 2:
                continue
            home = next((c for c in comps if c.get("homeAway") == "home"), None)
            away = next((c for c in comps if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            home_team = ((home.get("team") or {}).get("displayName")) or ""
            away_team = ((away.get("team") or {}).get("displayName")) or ""
            try:
                home_pts = int(float(home.get("score") or 0))
                away_pts = int(float(away.get("score") or 0))
            except ValueError:
                continue
            rows.append({
                "week": wk,
                "date": comp.get("date") or "",
                "home": home_team, "away": away_team,
                "home_pts": home_pts, "away_pts": away_pts,
            })

    # -----------------------------------------------------------------
    # STEP 2: Process rows week by week to insert byes correctly
    # -----------------------------------------------------------------

    # Get a master list of all teams that played in this range
    all_teams = set()
    for r in rows:
        all_teams.add(r["home"])
        all_teams.add(r["away"])

    # Group games by week for easy lookup
    games_by_week: Dict[int, List[Dict]] = {}
    for r in rows:
        games_by_week.setdefault(r["week"], []).append(r)

    # Initialize empty lists for all teams
    points_scored: Dict[str, List] = {team: [] for team in all_teams}
    points_allowed: Dict[str, List] = {team: [] for team in all_teams}

    # Loop through the *week range* (not the scraped rows)
    for wk in range(start_week, end_week + 1):
        teams_that_played_this_week = set()

        # Add scores for games that happened this week
        for game in games_by_week.get(wk, []):
            h, a = game["home"], game["away"]
            hp, ap = game["home_pts"], game["away_pts"]

            points_scored[h].append(hp)
            points_allowed[h].append(ap)
            points_scored[a].append(ap)
            points_allowed[a].append(hp)
            
            teams_that_played_this_week.add(h)
            teams_that_played_this_week.add(a)

        # Add "bye" for all other teams that didn't play
        for team in all_teams:
            if team not in teams_that_played_this_week:
                points_scored[team].append("bye")
                points_allowed[team].append("bye")

    # -----------------------------------------------------------------
    # STEP 3: Run tests and return
    # -----------------------------------------------------------------
    expected_games = end_week - start_week + 1
    scrape_points_test(points_scored, points_allowed, expected_games)
    return points_scored, points_allowed

def get_points(current_week: int, season_year: int = 2025):
    """
    Wrapper that uses JSON cache when available, delegates to scrape_points_by_team for missing weeks.
    """
    target_week = current_week - 1
    
    # Load existing data
    data = _load_json()
    most_recent = data["metadata"]["most_recent_week"]
    
    # If we have all needed data, return it
    if most_recent >= target_week:
        print(f"Loaded weeks 1-{target_week} from {JSON_FILE}")
        return data["scored"], data["allowed"]
    
    # Figure out what we need to scrape
    start = most_recent + 1
    end = target_week
    
    if most_recent > 0:
        print(f"Loading weeks 1-{most_recent} from {JSON_FILE}")
    print(f"Scraping weeks {start}-{end} from ESPN API...")
    
    # Call the scraping function
    new_scored, new_allowed = scrape_points_by_team(start, end, season_year)
    
    # Merge with existing data
    scored = data["scored"]
    allowed = data["allowed"]
    
    for team in new_scored:
        # If team is new (e.g., first week of scraping), pad previous weeks with byes
        if team not in scored:
            scored[team] = ["bye"] * most_recent
            allowed[team] = ["bye"] * most_recent
            
        scored.setdefault(team, []).extend(new_scored[team])
        allowed.setdefault(team, []).extend(new_allowed[team])
    
    # Save updated data
    data["metadata"]["most_recent_week"] = target_week
    data["scored"] = scored
    data["allowed"] = allowed
    _save_json(data)
    print(f"Saved updated data to {JSON_FILE}")
    
    return scored, allowed