#!/usr/bin/env python3
"""
Scrape NFL roster data (age, position, etc.) from ESPN
for all 32 teams.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import re

# All 32 NFL teams with ESPN URL slugs
NFL_TEAMS = [
    ('Arizona Cardinals', 'ari', 'arizona-cardinals'),
    ('Atlanta Falcons', 'atl', 'atlanta-falcons'),
    ('Baltimore Ravens', 'bal', 'baltimore-ravens'),
    ('Buffalo Bills', 'buf', 'buffalo-bills'),
    ('Carolina Panthers', 'car', 'carolina-panthers'),
    ('Chicago Bears', 'chi', 'chicago-bears'),
    ('Cincinnati Bengals', 'cin', 'cincinnati-bengals'),
    ('Cleveland Browns', 'cle', 'cleveland-browns'),
    ('Dallas Cowboys', 'dal', 'dallas-cowboys'),
    ('Denver Broncos', 'den', 'denver-broncos'),
    ('Detroit Lions', 'det', 'detroit-lions'),
    ('Green Bay Packers', 'gb', 'green-bay-packers'),
    ('Houston Texans', 'hou', 'houston-texans'),
    ('Indianapolis Colts', 'ind', 'indianapolis-colts'),
    ('Jacksonville Jaguars', 'jax', 'jacksonville-jaguars'),
    ('Kansas City Chiefs', 'kc', 'kansas-city-chiefs'),
    ('Las Vegas Raiders', 'lv', 'las-vegas-raiders'),
    ('Los Angeles Chargers', 'lac', 'los-angeles-chargers'),
    ('Los Angeles Rams', 'lar', 'los-angeles-rams'),
    ('Miami Dolphins', 'mia', 'miami-dolphins'),
    ('Minnesota Vikings', 'min', 'minnesota-vikings'),
    ('New England Patriots', 'ne', 'new-england-patriots'),
    ('New Orleans Saints', 'no', 'new-orleans-saints'),
    ('New York Giants', 'nyg', 'new-york-giants'),
    ('New York Jets', 'nyj', 'new-york-jets'),
    ('Philadelphia Eagles', 'phi', 'philadelphia-eagles'),
    ('Pittsburgh Steelers', 'pit', 'pittsburgh-steelers'),
    ('San Francisco 49ers', 'sf', 'san-francisco-49ers'),
    ('Seattle Seahawks', 'sea', 'seattle-seahawks'),
    ('Tampa Bay Buccaneers', 'tb', 'tampa-bay-buccaneers'),
    ('Tennessee Titans', 'ten', 'tennessee-titans'),
    ('Washington Commanders', 'wsh', 'washington-commanders'),
]

def scrape_team_roster(team_name, team_abbr, team_slug):
    """Scrape roster for a single team from ESPN."""
    url = f'https://www.espn.com/nfl/team/roster/_/name/{team_abbr}/{team_slug}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error fetching {team_name}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    players = []

    # ESPN uses Table__TD class for cells
    # Pattern: Name+Number, Position, Age, Height, Weight, Experience, College
    # With empty cells between players
    tds = soup.find_all('td', class_='Table__TD')

    cells = []
    for td in tds:
        text = td.get_text(strip=True)
        cells.append(text)

    # Process cells in groups - find pattern of 7 data cells
    i = 0
    while i < len(cells) - 6:
        # Skip empty cells
        if not cells[i]:
            i += 1
            continue

        # Check if this looks like a player name (contains letters and possibly numbers)
        name_cell = cells[i]
        if not re.search(r'[A-Za-z]', name_cell):
            i += 1
            continue

        # Check if next cell looks like a position (2-3 uppercase letters)
        if i + 1 < len(cells) and re.match(r'^[A-Z]{1,3}$', cells[i + 1]):
            try:
                # Extract name (remove jersey number from end)
                name_with_num = cells[i]
                # Split name from number - number is at the end
                match = re.match(r'^(.+?)(\d+)$', name_with_num)
                if match:
                    name = match.group(1).strip()
                    number = match.group(2)
                else:
                    name = name_with_num
                    number = ''

                position = cells[i + 1]
                age = cells[i + 2] if i + 2 < len(cells) else ''
                height = cells[i + 3] if i + 3 < len(cells) else ''
                weight = cells[i + 4] if i + 4 < len(cells) else ''
                experience = cells[i + 5] if i + 5 < len(cells) else ''
                college = cells[i + 6] if i + 6 < len(cells) else ''

                # Validate age looks like a number
                if age and age.isdigit():
                    player = {
                        'name': name,
                        'number': number,
                        'position': position,
                        'age': int(age),
                        'height': height,
                        'weight': weight.replace(' lbs', ''),
                        'experience': experience,
                        'college': college,
                        'team': team_name,
                        'team_abbr': team_abbr.upper(),
                    }
                    players.append(player)
                    i += 7
                    continue
            except Exception as e:
                pass

        i += 1

    return players


def main():
    all_players = []

    print(f"Scraping {len(NFL_TEAMS)} NFL team rosters from ESPN...")
    print("-" * 50)

    for i, (team_name, team_abbr, team_slug) in enumerate(NFL_TEAMS, 1):
        print(f"[{i}/32] {team_name}...", end=" ", flush=True)

        players = scrape_team_roster(team_name, team_abbr, team_slug)
        all_players.extend(players)

        print(f"Found {len(players)} players")

        # Be respectful - wait between requests
        if i < len(NFL_TEAMS):
            time.sleep(1.5)

    print("-" * 50)
    print(f"Total players scraped: {len(all_players)}")

    if all_players:
        # Create DataFrame
        df = pd.DataFrame(all_players)

        # Save to CSV
        csv_path = 'nfl_rosters_2025.csv'
        df.to_csv(csv_path, index=False)
        print(f"\nSaved to {csv_path}")

        # Also save to JSON for easy JS consumption
        json_path = 'nfl_rosters_2025.json'
        df.to_json(json_path, orient='records', indent=2)
        print(f"Saved to {json_path}")

        # Print sample
        print("\nSample data:")
        print(df[['name', 'position', 'age', 'team_abbr']].head(15).to_string())

        # Age statistics
        print("\nAge distribution:")
        print(df['age'].describe())

        print("\nPlayers by age:")
        print(df['age'].value_counts().sort_index())

        print("\nPlayers by position:")
        print(df['position'].value_counts())

    return all_players


if __name__ == '__main__':
    main()
