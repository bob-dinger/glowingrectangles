#!/usr/bin/env python3
"""
Scrape NFL roster data (age, position, etc.) from Pro Football Reference
for all 32 teams.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json

# All 32 NFL team abbreviations used by Pro Football Reference
NFL_TEAMS = {
    'Arizona Cardinals': 'crd',
    'Atlanta Falcons': 'atl',
    'Baltimore Ravens': 'rav',
    'Buffalo Bills': 'buf',
    'Carolina Panthers': 'car',
    'Chicago Bears': 'chi',
    'Cincinnati Bengals': 'cin',
    'Cleveland Browns': 'cle',
    'Dallas Cowboys': 'dal',
    'Denver Broncos': 'den',
    'Detroit Lions': 'det',
    'Green Bay Packers': 'gnb',
    'Houston Texans': 'htx',
    'Indianapolis Colts': 'clt',
    'Jacksonville Jaguars': 'jax',
    'Kansas City Chiefs': 'kan',
    'Las Vegas Raiders': 'rai',
    'Los Angeles Chargers': 'sdg',
    'Los Angeles Rams': 'ram',
    'Miami Dolphins': 'mia',
    'Minnesota Vikings': 'min',
    'New England Patriots': 'nwe',
    'New Orleans Saints': 'nor',
    'New York Giants': 'nyg',
    'New York Jets': 'nyj',
    'Philadelphia Eagles': 'phi',
    'Pittsburgh Steelers': 'pit',
    'San Francisco 49ers': 'sfo',
    'Seattle Seahawks': 'sea',
    'Tampa Bay Buccaneers': 'tam',
    'Tennessee Titans': 'oti',
    'Washington Commanders': 'was'
}

def scrape_team_roster(team_abbr, team_name, year=2025):
    """Scrape roster for a single team."""
    url = f'https://www.pro-football-reference.com/teams/{team_abbr}/{year}_roster.htm'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error fetching {team_name}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the roster table - it's usually id="roster"
    table = soup.find('table', {'id': 'roster'})

    if not table:
        print(f"  No roster table found for {team_name}")
        return []

    players = []

    # Get table body rows
    tbody = table.find('tbody')
    if not tbody:
        print(f"  No tbody found for {team_name}")
        return []

    rows = tbody.find_all('tr')

    for row in rows:
        # Skip header rows within tbody
        if row.get('class') and 'thead' in row.get('class'):
            continue

        cells = row.find_all(['td', 'th'])
        if len(cells) < 5:
            continue

        # Extract data - typical columns:
        # No., Player, Age, Pos, G, GS, Wt, Ht, College, BirthDate, Yrs, AV, ...
        player_data = {}

        for cell in cells:
            data_stat = cell.get('data-stat')
            if data_stat:
                # Get text content
                text = cell.get_text(strip=True)
                player_data[data_stat] = text

        if player_data.get('player'):
            player_data['team'] = team_name
            player_data['team_abbr'] = team_abbr
            players.append(player_data)

    return players

def main():
    all_players = []

    print(f"Scraping {len(NFL_TEAMS)} NFL team rosters...")
    print("-" * 50)

    for i, (team_name, team_abbr) in enumerate(NFL_TEAMS.items(), 1):
        print(f"[{i}/32] {team_name}...", end=" ")

        players = scrape_team_roster(team_abbr, team_name)
        all_players.extend(players)

        print(f"Found {len(players)} players")

        # Be respectful - wait between requests
        if i < len(NFL_TEAMS):
            time.sleep(2)

    print("-" * 50)
    print(f"Total players scraped: {len(all_players)}")

    if all_players:
        # Create DataFrame
        df = pd.DataFrame(all_players)

        # Select and rename key columns
        columns_to_keep = ['player', 'age', 'pos', 'team', 'team_abbr', 'weight', 'height',
                          'college', 'birth_date_mod', 'experience', 'g', 'gs', 'av']

        # Keep only columns that exist
        columns_to_keep = [c for c in columns_to_keep if c in df.columns]
        df = df[columns_to_keep]

        # Save to CSV
        csv_path = 'nfl_rosters_2025.csv'
        df.to_csv(csv_path, index=False)
        print(f"\nSaved to {csv_path}")

        # Also save to JSON for easy JS consumption
        json_path = 'nfl_rosters_2025.json'
        df.to_json(json_path, orient='records', indent=2)
        print(f"Saved to {json_path}")

        # Print sample and age distribution
        print("\nSample data:")
        print(df.head(10).to_string())

        if 'age' in df.columns:
            print("\nAge distribution:")
            # Convert age to numeric, handling any non-numeric values
            df['age_num'] = pd.to_numeric(df['age'], errors='coerce')
            print(df['age_num'].describe())

    return all_players

if __name__ == '__main__':
    main()
