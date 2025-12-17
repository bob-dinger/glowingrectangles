import csv
from collections import defaultdict
import json

# Track player snap counts by exact position for each team
team_players_by_pos = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

# Track formations
team_formations = defaultdict(lambda: defaultdict(int))

with open('pbp_participation_2023.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        possession_team = row.get('possession_team', '')
        formation = row.get('offense_formation', '')
        game_id = row.get('nflverse_game_id', '')

        if not possession_team or not game_id:
            continue

        # Figure out defensive team
        parts = game_id.split('_')
        if len(parts) >= 4:
            away_team = parts[2]
            home_team = parts[3]
            def_team = home_team if possession_team == away_team else away_team
        else:
            def_team = None

        # Track formation
        if formation:
            team_formations[possession_team][formation] += 1

        # Get offense data
        off_names = row.get('offense_names', '')
        off_positions = row.get('offense_positions', '')
        off_numbers = row.get('offense_numbers', '')

        if off_names and off_positions:
            names = off_names.split(';')
            positions = off_positions.split(';')
            numbers = off_numbers.split(';') if off_numbers else [''] * len(names)

            for name, pos, num in zip(names, positions, numbers):
                # Skip special teams positions when tracking offense
                if pos not in ['K', 'P', 'LS']:
                    team_players_by_pos[possession_team][f"OFF_{pos}"][(name, num)] += 1

        # Get defense data
        if def_team:
            def_names = row.get('defense_names', '')
            def_positions = row.get('defense_positions', '')
            def_numbers = row.get('defense_numbers', '')

            if def_names and def_positions:
                names = def_names.split(';')
                positions = def_positions.split(';')
                numbers = def_numbers.split(';') if def_numbers else [''] * len(names)

                for name, pos, num in zip(names, positions, numbers):
                    if pos not in ['K', 'P', 'LS']:
                        team_players_by_pos[def_team][f"DEF_{pos}"][(name, num)] += 1

# Build output with top starters at each position
output = {'teams': {}}

for team in sorted(team_players_by_pos.keys()):
    if not team:
        continue

    team_data = {
        'offense': {},
        'defense': {},
        'top_formation': None
    }

    # Get top formation
    if team_formations[team]:
        top_form = max(team_formations[team].items(), key=lambda x: x[1])
        team_data['top_formation'] = {'name': top_form[0], 'count': top_form[1]}

    for pos_key, players in team_players_by_pos[team].items():
        side = 'offense' if pos_key.startswith('OFF_') else 'defense'
        pos = pos_key.replace('OFF_', '').replace('DEF_', '')

        # Get top 3 at each position
        top_players = sorted(players.items(), key=lambda x: -x[1])[:3]
        team_data[side][pos] = [
            {'name': p[0], 'number': p[1], 'snaps': count}
            for (p, count) in top_players
        ]

    output['teams'][team] = team_data

# Save
with open('lineups_2023.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"Processed {len(output['teams'])} teams")

# Show sample
for sample_team in ['KC', 'SF']:
    if sample_team in output['teams']:
        print(f"\n=== {sample_team} ===")
        team = output['teams'][sample_team]
        print(f"Top formation: {team['top_formation']}")
        print("\nOffense starters:")
        for pos in ['QB', 'RB', 'WR', 'TE', 'C', 'G', 'T']:
            if pos in team['offense']:
                p = team['offense'][pos][0]
                print(f"  {pos}: #{p['number']} {p['name']} ({p['snaps']} snaps)")
        print("\nDefense starters:")
        for pos in ['DE', 'DT', 'NT', 'OLB', 'ILB', 'MLB', 'CB', 'FS', 'SS']:
            if pos in team['offense']:
                continue
            if pos in team['defense']:
                p = team['defense'][pos][0]
                print(f"  {pos}: #{p['number']} {p['name']} ({p['snaps']} snaps)")
