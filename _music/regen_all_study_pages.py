"""Regenerate all 12 study-list HTML pages with the new song_viewer.js-based template.

Reads each rebuild_*.py module's USER_LIST_* variable and feeds it to build_study_list_page.build_page.
Beatles-Study.html is built from a Supabase query (all rows with slug starting 'beatles_').
"""
import importlib, os, sys
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_study_list_page import build_page

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# (module name, list var, output filename, page title)
LISTS = [
    ('rebuild_studied_songs', 'USER_LIST',   'Guitar50.html',  'Guitar 50'),
    ('rebuild_study_2',       'USER_LIST_2', 'Guitar100.html', 'Guitar 100'),
    ('rebuild_guitar150',     'USER_LIST_3', 'Guitar150.html', 'Guitar 150'),
    ('rebuild_guitar200',     'USER_LIST_4', 'Guitar200.html', 'Guitar 200'),
    ('rebuild_guitar250',     'USER_LIST_5', 'Guitar250.html', 'Guitar 250'),
    ('rebuild_guitar300',     'USER_LIST_6', 'Guitar300.html', 'Guitar 300'),
    ('rebuild_guitar350',     'USER_LIST_7', 'Guitar350.html', 'Guitar 350'),
    ('rebuild_guitar400',     'USER_LIST_8', 'Guitar400.html', 'Guitar 400'),
    ('rebuild_guitar450',     'USER_LIST_9', 'Guitar450.html', 'Guitar 450'),
    ('rebuild_guitar500',     'USER_LIST_10','Guitar500.html', 'Guitar 500'),
    ('rebuild_guitar550',     'USER_LIST_11','Guitar550.html', 'Guitar 550'),
]


def beatles_list():
    """Build (title, artist) list from Supabase for all beatles_* slugs."""
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
    out, page = [], 0
    while True:
        r = sb.schema('parcels').table('songs').select('title,artist,slug').like('slug', 'beatles_%').range(page*1000, page*1000+999).execute()
        rows = r.data or []
        out.extend(rows)
        if len(rows) < 1000: break
        page += 1
    out.sort(key=lambda r: r['title'].lower())
    return [(r['title'], r['artist']) for r in out]


def main():
    for module_name, list_var, out_filename, page_title in LISTS:
        print(f'\n{page_title} ({module_name}.{list_var})')
        mod = importlib.import_module(module_name)
        song_list = getattr(mod, list_var)
        build_page(
            out_path=os.path.join(OUT_DIR, out_filename),
            page_title=page_title,
            song_list=song_list,
        )

    # Beatles list comes from Supabase, not a hardcoded var
    print('\nBeatles (from supabase: slug LIKE beatles_%)')
    beatles = beatles_list()
    print(f'  found {len(beatles)} Beatles slugs')
    build_page(
        out_path=os.path.join(OUT_DIR, 'Beatles-Study.html'),
        page_title='Beatles',
        song_list=beatles,
    )


if __name__ == '__main__':
    main()
