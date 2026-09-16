#!/usr/bin/env python3
"""
Last weekend's NFL plays -> one workbook, every column.

pbp (372 cols, nflfastR) joined to FTN charting (29 cols) on game+play id.
FTN is the only free source of snap-level alignment: QB under centre or
shotgun, backfield count, defenders in box, blitzers, motion, play action.

    python3 build_weekend_xlsx.py --dates 2026-09-13,2026-09-14
"""
import argparse, collections, csv, os, sys

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

HEAD = PatternFill('solid', fgColor='1F2430')
HF   = Font(color='FFFFFF', bold=True, size=9)
# the columns worth seeing first — the other ~380 are still there, just later
KEY = ['game_id','game_date','week','home_team','away_team','posteam','defteam',
       'qtr','time','down','ydstogo','yardline_100','play_type','desc',
       'qb_location','n_offense_backfield','n_defense_box','n_blitzers',
       'n_pass_rushers','is_motion','is_play_action','is_screen_pass','is_rpo',
       'is_no_huddle','starting_hash','shotgun','no_huddle','qb_dropback',
       'pass_length','pass_location','air_yards','run_location','run_gap',
       'yards_gained','epa','wpa','success','first_down','touchdown',
       'interception','fumble_lost','sack','penalty']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dates', default='2026-09-13,2026-09-14')
    ap.add_argument('--pbp', default='pbp2026.csv')
    ap.add_argument('--ftn', default='ftn2026.csv')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/nfl-last-weekend.xlsx'))
    a = ap.parse_args()
    dates = set(a.dates.split(','))

    pbp = [r for r in csv.DictReader(open(a.pbp)) if r['game_date'] in dates]
    ftn = {(r['nflverse_game_id'], r['nflverse_play_id']): r
           for r in csv.DictReader(open(a.ftn))}
    fcols = [c for c in (list(ftn.values())[0].keys() if ftn else [])
             if c not in ('nflverse_game_id', 'nflverse_play_id', 'season', 'week')]
    for r in pbp:
        f = ftn.get((r['game_id'], r['play_id']), {})
        for c in fcols: r[c] = f.get(c, '')

    allcols = list(pbp[0].keys())
    rest = [c for c in allcols if c not in KEY]
    order = [c for c in KEY if c in allcols] + rest
    print(f'{len(pbp)} plays, {len(order)} columns '
          f'({len(pbp[0]) - len(csv.DictReader(open(a.pbp)).fieldnames)} from FTN)')

    wb = Workbook(write_only=True)

    ws = wb.create_sheet('README')
    for line in [
        ('Last weekend in the NFL — every play, every column', 13, True),
        ('', 10, False),
        (f'{len(pbp)} plays  ·  {len({r["game_id"] for r in pbp})} games  ·  '
         f'{", ".join(sorted(dates))}', 10, False),
        ('', 10, False),
        ('SHEETS', 11, True),
        ('plays            every play, all ' + str(len(order)) + ' columns. The first '
         + str(len(KEY)) + ' are the', 10, False),
        ('                 ones worth reading; the rest is nflfastR in full.', 10, False),
        ('by team          formation and pressure rates per offence.', 10, False),
        ('by down          how the league plays each down.', 10, False),
        ('', 10, False),
        ('WHERE IT COMES FROM', 11, True),
        ('pbp: nflverse play_by_play_2026 (nflfastR). 372 columns of situation,', 10, False),
        ('EPA and win probability. Updated within a day or two of each game.', 10, False),
        ('', 10, False),
        ('FTN charting: the alignment columns — qb_location (U/S/P for under', 10, False),
        ('centre, shotgun, pistol), n_offense_backfield, n_defense_box,', 10, False),
        ('n_blitzers, n_pass_rushers, is_motion, is_play_action, is_screen_pass,', 10, False),
        ('is_rpo, is_no_huddle, starting_hash. Free through nflverse — do not', 10, False),
        ('pay FTN for it.', 10, False),
        ('', 10, False),
        ('WHAT IS NOT HERE', 11, True),
        ('Personnel groupings (11 personnel, 1RB-1TE-3WR). Those live in', 10, False),
        ('pbp_participation, whose latest season is 2025.', 10, False),
        ('', 10, False),
        ('Player XY coordinates. Zebra chip tracking goes to Next Gen Stats and', 10, False),
        ('is licensed to enterprise only. The sole free source is the Big Data', 10, False),
        ('Bowl on Kaggle, which releases past seasons, never current games.', 10, False),
    ]:
        c = ws.cell if False else None
        ws.append([line[0]])
    ws2 = None

    ws = wb.create_sheet('plays')
    ws.append(order)
    for r in pbp:
        ws.append([r.get(c, '') for c in order])

    # ---- by team ----
    def num(x):
        try: return float(x)
        except Exception: return None
    ws = wb.create_sheet('by team')
    ws.append(['offense', 'plays', 'shotgun %', 'under centre %', 'pistol %',
               'motion %', 'play action %', 'no huddle %', 'avg box',
               'avg blitzers', 'pass %', 'epa/play'])
    by = collections.defaultdict(list)
    for r in pbp:
        if r['posteam']: by[r['posteam']].append(r)
    for t in sorted(by):
        rs = by[t]
        ch = [r for r in rs if r.get('qb_location')]
        def pct(f, src=None):
            src = src or ch
            return round(100*sum(1 for r in src if f(r))/len(src), 1) if src else ''
        box = [num(r['n_defense_box']) for r in ch if num(r['n_defense_box'])]
        blz = [num(r['n_blitzers']) for r in ch if num(r['n_blitzers']) is not None]
        epa = [num(r['epa']) for r in rs if num(r['epa']) is not None]
        ws.append([t, len(rs),
                   pct(lambda r: r['qb_location'] == 'S'),
                   pct(lambda r: r['qb_location'] == 'U'),
                   pct(lambda r: r['qb_location'] == 'P'),
                   pct(lambda r: r['is_motion'] == 'TRUE'),
                   pct(lambda r: r['is_play_action'] == 'TRUE'),
                   pct(lambda r: r['is_no_huddle'] == 'TRUE'),
                   round(sum(box)/len(box), 2) if box else '',
                   round(sum(blz)/len(blz), 2) if blz else '',
                   pct(lambda r: r['play_type'] == 'pass',
                       [r for r in rs if r['play_type'] in ('pass', 'run')]),
                   round(sum(epa)/len(epa), 3) if epa else ''])

    # ---- by down ----
    ws = wb.create_sheet('by down')
    ws.append(['down', 'plays', 'shotgun %', 'motion %', 'play action %',
               'avg box', 'avg blitzers', 'pass %', 'epa/play', 'success %'])
    for d in ('1', '2', '3', '4'):
        rs = [r for r in pbp if r['down'] == d]
        ch = [r for r in rs if r.get('qb_location')]
        box = [num(r['n_defense_box']) for r in ch if num(r['n_defense_box'])]
        blz = [num(r['n_blitzers']) for r in ch if num(r['n_blitzers']) is not None]
        epa = [num(r['epa']) for r in rs if num(r['epa']) is not None]
        suc = [num(r['success']) for r in rs if num(r['success']) is not None]
        pr = [r for r in rs if r['play_type'] in ('pass', 'run')]
        ws.append([d, len(rs),
                   round(100*sum(1 for r in ch if r['qb_location']=='S')/len(ch),1) if ch else '',
                   round(100*sum(1 for r in ch if r['is_motion']=='TRUE')/len(ch),1) if ch else '',
                   round(100*sum(1 for r in ch if r['is_play_action']=='TRUE')/len(ch),1) if ch else '',
                   round(sum(box)/len(box),2) if box else '',
                   round(sum(blz)/len(blz),2) if blz else '',
                   round(100*sum(1 for r in pr if r['play_type']=='pass')/len(pr),1) if pr else '',
                   round(sum(epa)/len(epa),3) if epa else '',
                   round(100*sum(suc)/len(suc),1) if suc else ''])

    # ---- columns: a data dictionary, so the workbook documents itself ----
    ws = wb.create_sheet('columns')
    ws.append(['column', 'source', 'group', 'filled %', 'example'])
    GROUPS = {
     'identity': 'game_id play_id old_game_id season week season_type game_date stadium weather roof surface temp wind home_team away_team home_coach away_coach div_game location start_time nfl_api_id game_stadium',
     'situation': 'qtr down ydstogo yardline_100 side_of_field goal_to_go time quarter_seconds_remaining half_seconds_remaining game_seconds_remaining game_half quarter_end drive sp posteam posteam_type defteam score_differential total_home_score total_away_score posteam_score defteam_score posteam_timeouts_remaining defteam_timeouts_remaining',
     'the play': 'desc play_type play_type_nfl shotgun no_huddle qb_dropback qb_scramble qb_spike qb_kneel pass rush special pass_length pass_location air_yards yards_after_catch run_location run_gap yards_gained first_down success aborted_play play_deleted',
     'outcome': 'touchdown pass_touchdown rush_touchdown return_touchdown interception fumble fumble_lost fumble_forced safety sack tackled_for_loss complete_pass incomplete_pass penalty penalty_type penalty_yards two_point_attempt extra_point_result field_goal_result kick_distance td_team td_player_name',
     'EPA / WP': 'ep epa total_home_epa total_away_epa air_epa yac_epa comp_air_epa qb_epa xyac_epa xyac_mean_yardage xyac_success cp cpoe wp def_wp wpa vegas_wp vegas_wpa home_wp away_wp no_score_prob fg_prob td_prob safety_prob series_success series_result',
     'people': 'passer passer_player_id passer_player_name rusher rusher_player_name receiver receiver_player_name fantasy fantasy_player_name interception_player_name sack_player_name kicker_player_name punter_player_name',
     'drive': 'drive_real_start_time drive_play_count drive_time_of_possession drive_first_downs drive_inside20 drive_ended_with_score drive_quarter_start drive_quarter_end drive_yards_penalized drive_start_transition drive_end_transition drive_game_clock_start drive_game_clock_end drive_start_yard_line drive_end_yard_line fixed_drive fixed_drive_result',
    }
    grp = {}
    for g, names in GROUPS.items():
        for n in names.split(): grp[n] = g
    for c in order:
        vals = [r.get(c, '') for r in pbp]
        filled = sum(1 for v in vals if v not in ('', 'NA', None))
        eg = next((v for v in vals if v not in ('', 'NA', None)), '')
        ws.append([c, 'FTN' if c in fcols else 'pbp',
                   grp.get(c, 'other'),
                   round(100*filled/len(vals), 1),
                   str(eg)[:60]])

    # ---- datasets: what else nflverse publishes ----
    ws = wb.create_sheet('datasets')
    ws.append(['nflverse release', '2026 available?', 'what it is'])
    for row in [
      ('pbp', 'YES', 'play-by-play, 372 cols, nflfastR. The sheet named "plays".'),
      ('ftn_charting', 'YES', 'snap alignment: shotgun/under-centre, box, blitzers, motion.'),
      ('snap_counts', 'YES', 'snaps played per player per game, offence/defence/ST.'),
      ('rosters', 'YES', 'season roster with ids, height, weight, college.'),
      ('weekly_rosters', 'YES', 'roster as it stood each week.'),
      ('depth_charts', 'YES', 'depth chart by position and week.'),
      ('injuries', 'YES', 'injury report status.'),
      ('pfr_advstats', 'YES', 'Pro Football Reference advanced, weekly pass/rush/def.'),
      ('stats_player', 'YES', 'aggregated player stats, week and season.'),
      ('stats_team', 'YES', 'aggregated team stats.'),
      ('pbp_participation', 'no — 2025', 'PERSONNEL GROUPINGS (11 personnel etc). The main gap.'),
      ('nextgen_stats', 'no', 'NGS aggregates: time to throw, separation, rush yards over expected.'),
      ('players', 'n/a', 'player master table, all-time.'),
      ('schedules', 'n/a', 'game results and betting lines, all seasons.'),
      ('draft_picks / combine', 'n/a', 'draft and combine history.'),
      ('contracts', 'n/a', 'contract values by player.'),
      ('officials', 'n/a', 'referee crews per game.'),
      ('espn_data / misc', 'n/a', 'assorted joins.'),
      ('— NOT IN NFLVERSE —', '', ''),
      ('player XY tracking', 'no', 'Zebra chips -> NGS -> enterprise licence only. Free '
                                   'historical seasons via Kaggle Big Data Bowl.'),
      ('coverage scheme (man/zone)', 'no', 'PFF Pro $199 has it, but as season/week '
                                           'aggregates only — no play-level.'),
    ]: ws.append(list(row))

    # ---- everything else nflverse publishes for 2026 ----
    def add(sheet, path, note=''):
        if not os.path.exists(path): print(f'  (missing {path})'); return 0
        rows = list(csv.DictReader(open(path)))
        if not rows: return 0
        ws = wb.create_sheet(sheet)
        cols = list(rows[0].keys())
        ws.append(cols)
        for r in rows: ws.append([r.get(c, '') for c in cols])
        print(f'  {sheet:<18}{len(rows):>6} rows  {len(cols):>4} cols  {note}')
        return len(rows)

    print('other 2026 datasets:')
    add('snap counts', 'snap_counts_2026.csv', 'snaps + % by player/game, off/def/ST')
    add('player week', 'stats_player_week_2026.csv', 'every stat per player per week')
    for kind in ('pass', 'rush', 'rec', 'def'):
        add(f'pfr {kind}', f'advstats_week_{kind}_2026.csv',
            'PFR advanced — lags, often thin')

    wb.save(a.out)
    print(f'-> {a.out}')


if __name__ == '__main__':
    main()
