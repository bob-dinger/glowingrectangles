import csv
from collections import defaultdict
import json

# Read player stats
players = []
with open('player_stats_2024.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        players.append(row)

# Aggregate by player across all weeks (regular season only)
player_totals = defaultdict(lambda: {
    'name': '',
    'team': '',
    'position': '',
    'carries': 0,
    'rushing_yards': 0,
    'rushing_tds': 0,
    'fumbles': 0
})

for p in players:
    if p['season_type'] != 'REG':
        continue

    pid = p['player_id']
    player_totals[pid]['name'] = p['player_display_name']
    player_totals[pid]['team'] = p['recent_team']
    player_totals[pid]['position'] = p['position']

    # RB stats
    if p['carries']:
        player_totals[pid]['carries'] += int(float(p['carries']))
    if p['rushing_yards']:
        player_totals[pid]['rushing_yards'] += int(float(p['rushing_yards']))
    if p['rushing_tds']:
        player_totals[pid]['rushing_tds'] += int(float(p['rushing_tds']))
    if p['rushing_fumbles']:
        player_totals[pid]['fumbles'] += int(float(p['rushing_fumbles']))

# Group by team
teams = defaultdict(lambda: {'rbs': []})

for pid, stats in player_totals.items():
    team = stats['team']
    if not team:
        continue

    # Include RBs, QBs with rushing stats, and WRs who run
    if stats['carries'] >= 20:
        teams[team]['rbs'].append(stats)

# NFL team colors
team_colors = {
    'ARI': {'color': '#97233F', 'accent': '#000000'},
    'ATL': {'color': '#A71930', 'accent': '#000000'},
    'BAL': {'color': '#241773', 'accent': '#9E7C0C'},
    'BUF': {'color': '#00338D', 'accent': '#C60C30'},
    'CAR': {'color': '#0085CA', 'accent': '#101820'},
    'CHI': {'color': '#C83803', 'accent': '#0B162A'},
    'CIN': {'color': '#FB4F14', 'accent': '#000000'},
    'CLE': {'color': '#311D00', 'accent': '#FF3C00'},
    'DAL': {'color': '#003594', 'accent': '#869397'},
    'DEN': {'color': '#FB4F14', 'accent': '#002244'},
    'DET': {'color': '#0076B6', 'accent': '#B0B7BC'},
    'GB': {'color': '#203731', 'accent': '#FFB612'},
    'HOU': {'color': '#03202F', 'accent': '#A71930'},
    'IND': {'color': '#002C5F', 'accent': '#A2AAAD'},
    'JAX': {'color': '#101820', 'accent': '#D7A22A'},
    'KC': {'color': '#E31837', 'accent': '#FFB81C'},
    'LA': {'color': '#003594', 'accent': '#FFA300'},
    'LAC': {'color': '#0080C6', 'accent': '#FFC20E'},
    'LV': {'color': '#000000', 'accent': '#A5ACAF'},
    'MIA': {'color': '#008E97', 'accent': '#FC4C02'},
    'MIN': {'color': '#4F2683', 'accent': '#FFC62F'},
    'NE': {'color': '#002244', 'accent': '#C60C30'},
    'NO': {'color': '#D3BC8D', 'accent': '#101820'},
    'NYG': {'color': '#0B2265', 'accent': '#A71930'},
    'NYJ': {'color': '#125740', 'accent': '#000000'},
    'PHI': {'color': '#004C54', 'accent': '#A5ACAF'},
    'PIT': {'color': '#FFB612', 'accent': '#101820'},
    'SEA': {'color': '#002244', 'accent': '#69BE28'},
    'SF': {'color': '#AA0000', 'accent': '#B3995D'},
    'TB': {'color': '#D50A0A', 'accent': '#FF7900'},
    'TEN': {'color': '#0C2340', 'accent': '#4B92DB'},
    'WAS': {'color': '#5A1414', 'accent': '#FFB612'}
}

team_names = {
    'ARI': 'Arizona Cardinals',
    'ATL': 'Atlanta Falcons',
    'BAL': 'Baltimore Ravens',
    'BUF': 'Buffalo Bills',
    'CAR': 'Carolina Panthers',
    'CHI': 'Chicago Bears',
    'CIN': 'Cincinnati Bengals',
    'CLE': 'Cleveland Browns',
    'DAL': 'Dallas Cowboys',
    'DEN': 'Denver Broncos',
    'DET': 'Detroit Lions',
    'GB': 'Green Bay Packers',
    'HOU': 'Houston Texans',
    'IND': 'Indianapolis Colts',
    'JAX': 'Jacksonville Jaguars',
    'KC': 'Kansas City Chiefs',
    'LA': 'Los Angeles Rams',
    'LAC': 'Los Angeles Chargers',
    'LV': 'Las Vegas Raiders',
    'MIA': 'Miami Dolphins',
    'MIN': 'Minnesota Vikings',
    'NE': 'New England Patriots',
    'NO': 'New Orleans Saints',
    'NYG': 'New York Giants',
    'NYJ': 'New York Jets',
    'PHI': 'Philadelphia Eagles',
    'PIT': 'Pittsburgh Steelers',
    'SEA': 'Seattle Seahawks',
    'SF': 'San Francisco 49ers',
    'TB': 'Tampa Bay Buccaneers',
    'TEN': 'Tennessee Titans',
    'WAS': 'Washington Commanders'
}

team_data = []

for team_abbr, data in teams.items():
    if not data['rbs']:
        continue

    # Get top rushers by carries
    top_rbs = sorted(data['rbs'], key=lambda x: x['carries'], reverse=True)[:5]

    # Calculate team totals
    team_carries = sum(r['carries'] for r in top_rbs)
    team_yards = sum(r['rushing_yards'] for r in top_rbs)
    team_tds = sum(r['rushing_tds'] for r in top_rbs)

    colors = team_colors.get(team_abbr, {'color': '#666666', 'accent': '#999999'})

    team_data.append({
        'abbr': team_abbr,
        'name': team_names.get(team_abbr, team_abbr),
        'color': colors['color'],
        'accent': colors['accent'],
        'team_carries': team_carries,
        'team_yards': team_yards,
        'team_tds': team_tds,
        'rushers': [
            {
                'name': r['name'],
                'pos': r['position'],
                'carries': r['carries'],
                'yards': r['rushing_yards'],
                'tds': r['rushing_tds'],
                'ypc': round(r['rushing_yards'] / r['carries'], 1) if r['carries'] > 0 else 0
            }
            for r in top_rbs
        ]
    })

# Sort by team name
team_data.sort(key=lambda x: x['name'])

# Output as JSON
with open('rb_rushing_2024.json', 'w') as f:
    json.dump(team_data, f, indent=2)

print(f"Generated data for {len(team_data)} teams")
for t in team_data:
    print(f"  {t['abbr']}: {len(t['rushers'])} rushers, {t['team_yards']} total yards")
