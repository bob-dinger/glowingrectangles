"""Block combiner. A song = a sequence of BLOCKS; a block = a chord-progression
crossed with a melodic phrase. The melodic phrase has four dials:
    focus     — the reciting tone (scale degree 1-7 the phrase orbits)
    register  — octave band (0 = home, -1 = low, +1 = high)
    motion    — how it moves around the focus: orbit | arch | descend | rise
    rhythm    — per-measure cell pattern (Q=3 quarters, L=long note, R=rest)

Reference: Under the Bridge = verse [axis x focus-3 @0 orbit] + chorus
[ii-I-V-ii x focus-6 @-1 orbit] — the chorus DROPS register, which is the whole
emotional move. Edit RECIPES at the bottom and re-run.

    themap_venv/python build_blocks.py        # writes pastes to ~/Desktop/blocks/
"""
import json, os, math

# ---------------- chord blocks (8-measure root sequences; 4-cells auto-loop) ----------------
CHORD_BLOCKS = {
    'axis':       [1,5,6,4],            # I V vi IV
    'doowop':     [1,6,4,5],            # I vi IV V (50s)
    'pillars':    [1,4,5,4],            # I IV V IV
    'viIV':       [6,4],                # vi IV vamp
    'wonderwall': [6,1,5,2],            # vi I V ii
    'ii_I_V_ii':  [2,1,5,2],            # Under the Bridge chorus
    'ii_V_I':     [2,5,1,1],            # jazzy resolve
    'IV_V_I':     [4,5,1,1],
    'andalusian': [6,5,4,3],            # descending minor-ish (vi V IV iii)
}
def prog8(name):
    c = CHORD_BLOCKS[name]
    return [c[m % len(c)] for m in range(8)]

# ---------------- rhythm cells per measure ----------------
RHYTHM = {
    'A': ['Q','L','Q','L','Q','Q','L','R'],
    'B': ['Q','Q','L','Q','Q','L','Q','L'],
    'C': ['L','Q','L','Q','Q','L','Q','R'],
    'flow': ['Q','Q','Q','Q','Q','Q','Q','L'],
}

# ---------------- melody engine ----------------
def _ctones(root):
    sds=[root,((root-1+2)%7)+1,((root-1+4)%7)+1]
    return sorted({t-1+7*k for t in sds for k in (-2,-1,0,1,2)})
def _snap(desired, root):
    return min(_ctones(root), key=lambda i:abs(i-desired))
def _shape(motion, m):
    x=m/7.0
    return {'orbit':0.0,'arch':4*math.sin(math.pi*x),'descend':4*(1-x),'rise':4*x}[motion]

def gen_melody(prog, focus, register, motion, rhythm):
    """Return list of (pitch_index, beat, dur). pitch_index = octave*7 + (sd-1)."""
    F = register*7 + (focus-1)
    pat = RHYTHM[rhythm]
    # per-measure downbeat target: focus (+ contour shape), snapped to a chord tone
    tgt = [_snap(F + _shape(motion, m), prog[m]) for m in range(8)]
    notes=[]
    for m in range(8):
        b0=1+3*m; r=pat[m]
        if r=='R': continue
        if r=='L':
            notes.append((tgt[m], b0, 3)); continue
        # QQQ
        if motion=='orbit':
            a=tgt[m]; cell=[a, a-1, a]          # recite with a lower-neighbor turn
        else:
            a=tgt[m]; b=tgt[m+1] if m<7 else tgt[m]
            cell=[a+round(j*(b-a)/3.0) for j in range(3)]   # walk stepwise toward next downbeat
        for j,p in enumerate(cell): notes.append((p, b0+j, 1))
    return notes

# ---------------- assemble ----------------
def _chord_objs(prog, base):
    return [{"root":prog[m],"beat":base+3*m,"duration":3,"type":5,"inversion":0,"applied":0,"adds":[],
             "omits":[],"alterations":[],"suspensions":[],"substitutions":[],"pedal":None,"alternate":"",
             "borrowed":"","isRest":False,"recordingEndBeat":None} for m in range(8)]
def _note_objs(notes, base):
    return [{"sd":str((p%7)+1),"octave":p//7,"beat":base+bt-1,"duration":d,"isRest":False,"recordingEndBeat":None}
            for (p,bt,d) in notes]

def build_song(blocks, form, key="C", bpm=110):
    """blocks: {label: (chord_block, focus, register, motion, rhythm)}; form: list of labels."""
    # render each unique block once
    rendered={lab:(prog8(cb), gen_melody(prog8(cb),f,reg,mo,rh)) for lab,(cb,f,reg,mo,rh) in blocks.items()}
    chords=[]; notes=[]; sections=[]
    for i,lab in enumerate(form):
        base=1+i*24; prog,mel=rendered[lab]
        sections.append({"beat":base,"name":lab})
        chords+=_chord_objs(prog, base); notes+=_note_objs(mel, base)
    return {"keys":[{"beat":1,"scale":"major","tonic":key}],"notes":notes,"chords":chords,
            "meters":[{"beat":1,"beatUnit":1,"numBeats":3}],
            "tempos":[{"bpm":bpm,"beat":1,"swingBeat":0.5,"swingFactor":0}],
            "sections":sections,"endBeat":len(form)*24+1,"audioTracks":[],"version":1}

# ---------------- RECIPES (edit these) ----------------
RECIPES = {
  # (chord_block, focus, register, motion, rhythm)
  'under_the_bridge': ({
      'V': ('axis',       3, 0, 'orbit', 'A'),    # verse: recite 3, home octave
      'C': ('ii_I_V_ii',  6,-1, 'orbit', 'A'),    # chorus: recite 6, DROP to low octave
  }, ['V','V','C','V','V','C']),

  'bright_anthem': ({                              # same UTB blocks but chorus LIFTS instead of drops
      'V': ('axis',       3, 0, 'orbit', 'A'),
      'C': ('ii_I_V_ii',  6, 0, 'arch',  'B'),
  }, ['V','V','C','V','V','C']),

  'stack_ABABACC': ({
      'A': ('axis',       5, 0, 'arch',    'A'),
      'B': ('doowop',     3, 0, 'descend', 'B'),
      'C': ('ii_V_I',     1, 0, 'descend', 'A'),
  }, ['A','B','A','B','A','C','C']),
}

if __name__=='__main__':
    out=os.path.expanduser('~/Desktop/blocks'); os.makedirs(out,exist_ok=True)
    for name,(blocks,form) in RECIPES.items():
        obj=build_song(blocks, form)
        open(os.path.join(out,name+".txt"),'w').write(json.dumps(obj,separators=(',',':'),ensure_ascii=False))
        print(f"  {name+'.txt':26} form={' '.join(form)}  ({len(obj['chords'])} bars)")
    print(f"\nwrote {len(RECIPES)} songs to {out}/")
