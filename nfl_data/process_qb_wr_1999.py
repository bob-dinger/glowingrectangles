import csv
from collections import defaultdict
import json

# Read player stats
players = []
with open('player_stats_1999.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        players.append(row)

# Aggregate by player across all weeks (regular season only)
player_totals = defaultdict(lambda: {
    'name': '',
    'team': '',
    'position': '',
    'attempts': 0,
    'completions': 0,
    'passing_yards': 0,
    'passing_tds': 0,
    'targets': 0,
    'receptions': 0,
    'receiving_yards': 0,
    'receiving_tds': 0
})

for p in players:
    if p['season_type'] != 'REG':
        continue

    pid = p['player_id']
    player_totals[pid]['name'] = p['player_display_name'] or p['player_name']
    player_totals[pid]['team'] = p['recent_team']
    player_totals[pid]['position'] = p['position']

    # QB stats
    if p['attempts']:
        player_totals[pid]['attempts'] += int(p['attempts'])
    if p['completions']:
        player_totals[pid]['completions'] += int(p['completions'])
    if p['passing_yards']:
        player_totals[pid]['passing_yards'] += int(float(p['passing_yards']))
    if p['passing_tds']:
        player_totals[pid]['passing_tds'] += int(p['passing_tds'])

    # Receiver stats
    if p['targets']:
        player_totals[pid]['targets'] += int(float(p['targets']))
    if p['receptions']:
        player_totals[pid]['receptions'] += int(float(p['receptions']))
    if p['receiving_yards']:
        player_totals[pid]['receiving_yards'] += int(float(p['receiving_yards']))
    if p['receiving_tds']:
        player_totals[pid]['receiving_tds'] += int(float(p['receiving_tds']))

# Group by team
teams = defaultdict(lambda: {'qbs': [], 'receivers': []})

for pid, stats in player_totals.items():
    team = stats['team']
    if not team:
        continue

    if stats['position'] == 'QB' and stats['attempts'] >= 100:
        teams[team]['qbs'].append(stats)
    elif stats['position'] in ['WR', 'TE', 'RB'] and stats['targets'] >= 20:
        teams[team]['receivers'].append(stats)

# Sort and select main QB and top receivers per team
team_data = []

# NFL team colors (1999 teams - some different!)
# Note: Data uses modern team codes, so we map LA->STL, LAC->SD, LV->OAK
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
    'IND': {'color': '#002C5F', 'accent': '#A2AAAD'},
    'JAX': {'color': '#101820', 'accent': '#D7A22A'},
    'KC': {'color': '#E31837', 'accent': '#FFB81C'},
    'MIA': {'color': '#008E97', 'accent': '#FC4C02'},
    'MIN': {'color': '#4F2683', 'accent': '#FFC62F'},
    'NE': {'color': '#002244', 'accent': '#C60C30'},
    'NO': {'color': '#D3BC8D', 'accent': '#101820'},
    'NYG': {'color': '#0B2265', 'accent': '#A71930'},
    'NYJ': {'color': '#125740', 'accent': '#000000'},
    'LV': {'color': '#000000', 'accent': '#A5ACAF'},   # Data uses LV but was Oakland in 1999
    'PHI': {'color': '#004C54', 'accent': '#A5ACAF'},
    'PIT': {'color': '#FFB612', 'accent': '#101820'},
    'LAC': {'color': '#0080C6', 'accent': '#FFC20E'},  # Data uses LAC but was San Diego in 1999
    'SEA': {'color': '#002244', 'accent': '#69BE28'},
    'SF': {'color': '#AA0000', 'accent': '#B3995D'},
    'LA': {'color': '#003594', 'accent': '#FFA300'},   # Data uses LA but was St. Louis in 1999
    'TB': {'color': '#D50A0A', 'accent': '#FF7900'},
    'TEN': {'color': '#0C2340', 'accent': '#4B92DB'},  # Titans just moved from Houston
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
    'IND': 'Indianapolis Colts',
    'JAX': 'Jacksonville Jaguars',
    'KC': 'Kansas City Chiefs',
    'MIA': 'Miami Dolphins',
    'MIN': 'Minnesota Vikings',
    'NE': 'New England Patriots',
    'NO': 'New Orleans Saints',
    'NYG': 'New York Giants',
    'NYJ': 'New York Jets',
    'LV': 'Oakland Raiders',       # Data uses LV but was Oakland in 1999
    'PHI': 'Philadelphia Eagles',
    'PIT': 'Pittsburgh Steelers',
    'LAC': 'San Diego Chargers',   # Data uses LAC but was San Diego in 1999
    'SEA': 'Seattle Seahawks',
    'SF': 'San Francisco 49ers',
    'LA': 'St. Louis Rams',        # Data uses LA but was St. Louis in 1999
    'TB': 'Tampa Bay Buccaneers',
    'TEN': 'Tennessee Titans',
    'WAS': 'Washington Redskins'
}

for team_abbr, data in teams.items():
    if not data['qbs'] or not data['receivers']:
        continue

    # Get main QB (most attempts)
    main_qb = max(data['qbs'], key=lambda x: x['attempts'])

    # Get top 5 receivers by receptions
    top_receivers = sorted(data['receivers'], key=lambda x: x['receptions'], reverse=True)[:5]

    colors = team_colors.get(team_abbr, {'color': '#666666', 'accent': '#999999'})

    team_data.append({
        'abbr': team_abbr,
        'name': team_names.get(team_abbr, team_abbr),
        'color': colors['color'],
        'accent': colors['accent'],
        'qb': {
            'name': main_qb['name'],
            'attempts': main_qb['attempts'],
            'completions': main_qb['completions'],
            'yards': main_qb['passing_yards'],
            'tds': main_qb['passing_tds']
        },
        'receivers': [
            {
                'name': r['name'],
                'pos': r['position'],
                'targets': r['targets'],
                'receptions': r['receptions'],
                'yards': r['receiving_yards'],
                'tds': r['receiving_tds']
            }
            for r in top_receivers
        ]
    })

# Sort by team name
team_data.sort(key=lambda x: x['name'])

# Output as JSON
with open('qb_wr_connections_1999.json', 'w') as f:
    json.dump(team_data, f, indent=2)

print(f"Generated data for {len(team_data)} teams")
for t in team_data:
    print(f"  {t['abbr']}: {t['qb']['name']} -> {len(t['receivers'])} receivers")
