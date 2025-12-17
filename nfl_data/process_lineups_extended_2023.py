import csv
from collections import defaultdict
import json

# Load draft data - more reliable for draft info
player_draft = {}
with open('draft_picks.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['pfr_player_name']
        if name:
            # Keep most recent draft entry (in case of duplicates)
            player_draft[name.lower()] = {
                'draft_round': row['round'],
                'draft_pick': row['pick'],
                'draft_year': row['season']
            }

print(f"Loaded {len(player_draft)} draft picks")

# Load contracts data - for salary info
player_contracts = {}
with open('historical_contracts.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['player']
        try:
            apy = int(float(row['apy'] or 0))
        except:
            apy = 0

        # Keep the highest paying contract
        if name.lower() not in player_contracts or apy > player_contracts[name.lower()].get('apy', 0):
            player_contracts[name.lower()] = {
                'apy': apy,
                'years': row['years'],
                'guaranteed': row['guaranteed']
            }

print(f"Loaded {len(player_contracts)} player contracts")

# Load existing lineup data
with open('lineups_2023.json', 'r') as f:
    lineup_data = json.load(f)

def normalize_name(name):
    """Remove suffixes and normalize a name"""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv', ' v']:
        name = name.replace(suffix, '')
    return name.strip()

def find_match(name, data_dict):
    """Try to find a player in a dictionary with fuzzy matching"""
    name_lower = name.lower()

    # Exact match
    if name_lower in data_dict:
        return data_dict[name_lower]

    # Try normalized name (remove Jr., Sr., III, etc.)
    clean_name = normalize_name(name)
    if clean_name in data_dict:
        return data_dict[clean_name]

    # Try matching against normalized dict keys
    for dict_name, data in data_dict.items():
        if normalize_name(dict_name) == clean_name:
            return data

    # Try matching first + last name (e.g., "T.J. Watt" vs "TJ Watt")
    name_parts = clean_name.split()
    if len(name_parts) >= 2:
        last_name = name_parts[-1]
        first_part = name_parts[0].replace('.', '')

        for dict_name, data in data_dict.items():
            dict_clean = normalize_name(dict_name)
            dict_parts = dict_clean.split()
            if len(dict_parts) >= 2:
                dict_last = dict_parts[-1]
                dict_first = dict_parts[0].replace('.', '')

                if last_name == dict_last:
                    # Check first name/initial match
                    if first_part == dict_first:
                        return data
                    # Check if one is initial of the other
                    if len(first_part) <= 2 and dict_first.startswith(first_part):
                        return data
                    if len(dict_first) <= 2 and first_part.startswith(dict_first):
                        return data

    return None

# Enrich with draft/contract info
for team_code, team in lineup_data['teams'].items():
    for side in ['offense', 'defense']:
        for pos, players in team[side].items():
            for player in players:
                name = player['name']

                # Get draft info
                draft_data = find_match(name, player_draft)
                if draft_data:
                    player['draft_round'] = draft_data['draft_round']
                    player['draft_pick'] = draft_data['draft_pick']
                else:
                    player['draft_round'] = ''
                    player['draft_pick'] = ''

                # Get salary info
                contract_data = find_match(name, player_contracts)
                if contract_data:
                    player['salary'] = contract_data['apy']
                else:
                    player['salary'] = 0

# Save enriched data
with open('lineups_extended_2023.json', 'w') as f:
    json.dump(lineup_data, f, indent=2)

print("Saved enriched lineup data")

# Show sample
for sample_team in ['KC', 'LA']:
    if sample_team in lineup_data['teams']:
        print(f"\n=== {sample_team} Offense ===")
        team = lineup_data['teams'][sample_team]
        for pos in ['QB', 'RB', 'WR', 'TE', 'C', 'G', 'T']:
            if pos in team['offense'] and team['offense'][pos]:
                p = team['offense'][pos][0]
                draft = f"R{p.get('draft_round', '?')}" if p.get('draft_round') else "UDFA"
                salary = f"${p.get('salary', 0):,}/yr" if p.get('salary') else "N/A"
                print(f"  {pos}: {p['name']} - {draft}, {salary}")

        print(f"\n=== {sample_team} Defense ===")
        for pos in ['DE', 'DT', 'NT', 'OLB', 'ILB', 'MLB', 'CB', 'FS', 'SS']:
            if pos in team['defense'] and team['defense'][pos]:
                p = team['defense'][pos][0]
                draft = f"R{p.get('draft_round', '?')}" if p.get('draft_round') else "UDFA"
                salary = f"${p.get('salary', 0):,}/yr" if p.get('salary') else "N/A"
                print(f"  {pos}: {p['name']} - {draft}, {salary}")
