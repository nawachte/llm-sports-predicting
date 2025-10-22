# nfl_scraper_utils.py

import requests
from typing import Dict, List, Tuple
from urllib.parse import urlparse

CORE_WEEK_EVENTS = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/types/2/weeks/{week}/events"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"

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

def scrape_points_by_team(current_week: int, season_year: int = 2025):
    if current_week < 1:
        raise ValueError("current_week must be >= 1")

    rows = []
    for wk in range(1, max(1, current_week)):
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

    rows.sort(key=lambda r: (r["week"], r["date"]))

    points_scored, points_allowed = {}, {}
    for r in rows:
        h, a = r["home"], r["away"]
        hp, ap = r["home_pts"], r["away_pts"]
        points_scored.setdefault(h, []).append(hp)
        points_allowed.setdefault(h, []).append(ap)
        points_scored.setdefault(a, []).append(ap)
        points_allowed.setdefault(a, []).append(hp)

    # ---------- insert bye placeholders ----------
    all_teams = list(points_scored.keys())
    for team in all_teams:
        games = len(points_scored[team])
        expected_games = current_week - 1
        # one "bye" for every missing week (usually 0 or 1)
        byes = expected_games - games
        for _ in range(byes):
            points_scored[team].append("bye")
            points_allowed[team].append("bye")

    scrape_points_test(points_scored, points_allowed, current_week - 1)
    return points_scored, points_allowed