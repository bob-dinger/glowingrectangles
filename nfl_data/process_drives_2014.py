import csv
from collections import defaultdict
import json

# Read play-by-play data
games = defaultdict(lambda: {
    'game_id': '',
    'week': 0,
    'home_team': '',
    'away_team': '',
    'home_score': 0,
    'away_score': 0,
    'drives': []
})

drive_data = defaultdict(lambda: {
    'team': '',
    'yards': 0,
    'result': '',
    'plays': 0,
    'start_yard': 0,
    'scored': False
})

with open('pbp_2014.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        game_id = row['game_id']
        week = row['week']

        # Skip non-regular season
        if row['season_type'] != 'REG':
            continue

        if not week or not game_id:
            continue

        games[game_id]['game_id'] = game_id
        games[game_id]['week'] = int(week)
        games[game_id]['home_team'] = row['home_team']
        games[game_id]['away_team'] = row['away_team']

        if row['home_score']:
            games[game_id]['home_score'] = int(row['home_score'])
        if row['away_score']:
            games[game_id]['away_score'] = int(row['away_score'])

        # Track drives
        drive_num = row['fixed_drive']
        posteam = row['posteam']

        if drive_num and posteam:
            drive_key = f"{game_id}_{drive_num}"
            drive_data[drive_key]['team'] = posteam
            drive_data[drive_key]['game_id'] = game_id
            drive_data[drive_key]['drive_num'] = int(drive_num)

            if row['fixed_drive_result']:
                drive_data[drive_key]['result'] = row['fixed_drive_result']

            # Get yards gained on this play
            yards = 0
            if row['yards_gained']:
                try:
                    yards = int(float(row['yards_gained']))
                except:
                    pass
            drive_data[drive_key]['yards'] += yards
            drive_data[drive_key]['plays'] += 1

            if row['drive_ended_with_score'] == '1':
                drive_data[drive_key]['scored'] = True

# Assign drives to games
for drive_key, drive in drive_data.items():
    game_id = drive['game_id']
    if game_id in games:
        games[game_id]['drives'].append({
            'drive_num': drive['drive_num'],
            'team': drive['team'],
            'yards': drive['yards'],
            'result': drive['result'],
            'plays': drive['plays'],
            'scored': drive['scored']
        })

# Sort drives within each game
for game in games.values():
    game['drives'].sort(key=lambda x: x['drive_num'])

# Group by week
weeks = defaultdict(list)
for game in games.values():
    weeks[game['week']].append(game)

# Sort games within each week
for week in weeks:
    weeks[week].sort(key=lambda x: x['game_id'])

# Output
output = {
    'weeks': {}
}

for week_num in sorted(weeks.keys()):
    output['weeks'][week_num] = weeks[week_num]

with open('drives_2014.json', 'w') as f:
    json.dump(output, f)

print(f"Processed {len(games)} games across {len(weeks)} weeks")
for w in sorted(weeks.keys())[:5]:
    print(f"  Week {w}: {len(weeks[w])} games")
