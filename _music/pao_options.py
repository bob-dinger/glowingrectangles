#!/usr/bin/env python3
"""
Candidate imagery for a chord progression, so every song-part can have its
OWN scene instead of reusing a fixed grid.

The only rule is the initial consonant sound. Any word with the right sound
decodes to the right chord, so you are free to pick imagery that suits the
song — which makes the picture memorable twice over.

    python3 pao_options.py "F C G Am"          # all options per slot
    python3 pao_options.py "F C G Am" --pick 6  # six ready-made scenes
    python3 pao_options.py "Am F C" --prompt    # + an image prompt

Slots, in order: Person, Action, Object, Place. Progressions longer than four
wrap into a second scene.
"""
import argparse, random, re, sys

SOUNDS = {
    'C':  'k · hard c · q',
    'F':  'f · v · ph',
    'G':  'j · sh · ch · g (hard AND soft)',
    'Am': 's · z',
    'Dm': 't · d',
    'D':  'th · w',
    'Em': 'm',
    'E':  'r · wr',
    'A#': 'p · b',
}

W = {
 # C is the /k/ sound only. Every g-word moved to G, so "g is always G"
 # holds with no soft/hard exception to remember.
 'C': dict(
  person="cowboy king queen captain clown cook cat camel crow crab caveman "
         "coach conductor carpenter kangaroo courier".split(),
  action="kicking climbing catching carving crushing carrying combing cooking "
         "counting casting crawling cutting".split(),
  object="cake key coin cage crown cactus kite comb cup candle camera clock "
         "cannon compass kettle crate".split(),
  place="casino castle cave canyon cathedral kitchen cabin cornfield crater "
        "courtyard campsite".split()),
 'F': dict(
  person="pharaoh vampire viking firefighter fisherman fencer photographer "
         "vicar violinist vet farmer ferryman florist valet villain fairy "
         "falcon fox flamingo frog".split(),
  action="frying folding flipping freezing filming fanning flinging flooding "
         "vacuuming varnishing filling feeding floating fetching".split(),
  object="fork flag violin vase feather flute fridge van funnel vest phone "
         "fan flashlight fiddle fossil flower".split(),
  place="volcano vault factory forest ferry fountain village field farm "
        "foundry valley fairground".split()),
 # G takes EVERY g spelling, hard and soft, plus j/sh/ch.
 'G': dict(
  person="jockey judge chef shepherd sheriff giant genie jester janitor "
         "jeweller chimp giraffe sheep shark chicken jaguar chauffeur "
         "gardener golfer goalie gorilla guard guitarist goat goose".split(),
  action="juggling chasing chopping shaving shaking charging shoving "
         "shattering jabbing jamming sharpening chewing shovelling jumping "
         "guarding galloping grabbing gripping".split(),
  object="gem shoe shell jug chain chair jet shield shovel chisel jar "
         "jacket chalk cherry chandelier guitar glove gate goggles".split(),
  place="jungle church gym shed ship jail chapel shipyard junkyard chalet "
        "garage garden gallery".split()),
 'Am': dict(
  person="samurai sailor soldier surgeon spy zookeeper scientist skeleton "
         "sculptor snake swan seal squirrel zebra scarecrow senator".split(),
  action="sawing sinking squeezing swimming salting zipping stacking spinning "
         "sealing sweeping sliding sprinkling stitching smashing snapping".split(),
  object="sponge sword saddle sock suitcase seashell sandwich sail sieve "
         "scissors saxophone star seed scarf".split(),
  place="swamp zoo stadium submarine sauna city cellar salon station sewer".split()),
 'Dm': dict(
  person="diver doctor teacher tailor detective dentist drummer toddler "
         "dancer deer dog duck dolphin turtle tiger twin".split(),
  action="dancing digging tearing tying dripping dunking dusting towing "
         "dragging dipping tickling tipping toasting trimming".split(),
  object="drum table tooth dart tyre tent torch dice dagger doll drill "
         "towel trumpet telescope domino".split(),
  place="tunnel dam desert dungeon dock tower temple diner den dairy".split()),
 'D': dict(
  person="thief thug therapist wizard welder wrestler waiter warrior witch "
         "woodcutter whale wolf worm".split(),
  action="throwing thawing threading thumping welding waving washing weighing "
         "winding whipping whistling".split(),
  object="thumb thorn thread thermos throne wheel wand whistle wagon window watch".split(),
  place="theatre thicket waterfall warehouse well windmill wall workshop".split()),
 'Em': dict(
  person="mermaid monk mechanic magician miner mummy mayor milkman mouse "
         "moth monkey mole moose".split(),
  action="mowing melting milking mixing marching mopping mending moulding "
         "mashing measuring".split(),
  object="magnet mask mirror mug map mop medal moon mushroom microphone "
         "matchbox marble".split(),
  place="mine mill museum marsh mountain market maze mosque meadow".split()),
 'E': dict(
  person="robot referee rancher racer ranger rabbi rapper rabbit raven "
         "rhino rooster rat".split(),
  action="rowing running riding ripping rolling raking wrapping wringing "
         "reeling roasting rinsing".split(),
  object="rocket rope ring radio rake rug rifle raft ribbon razor radish".split(),
  place="roof river ranch ruins racetrack reef refinery rink".split()),
 'A#': dict(
  person="ballerina pirate baker boxer pilot plumber priest bandit butcher "
         "painter bear bat bee parrot penguin panda".split(),
  action="boxing painting pushing packing burning blowing pouring biting "
          "bouncing plucking pinning patching polishing bending".split(),
  object="piano book ball bell box balloon bucket pipe basket broom bottle "
         "brick paddle pillow".split(),
  place="bridge bakery bank beach palace prison barn basement ballroom pier".split()),
}

ROLES = ['person', 'action', 'object', 'place']


def parse(prog):
    out = []
    for x in [t for t in re.split(r'[\s,\-–>|]+', prog.strip()) if t]:
        c = {'am':'Am','dm':'Dm','em':'Em','a#':'A#','bb':'A#','c':'C',
             'd':'D','e':'E','f':'F','g':'G'}.get(x.lower())
        if not c: sys.exit(f'unknown chord {x!r}')
        if not out or out[-1] != c: out.append(c)      # collapse repeats
    return out


# words that are already plural take no article: "a goggles" reads as a typo
# and an image model will draw something odd for it
PLURAL = {'goggles', 'scissors', 'ruins', 'dice', 'dominoes'}


def art(w, cap=False):
    if w in PLURAL: return w
    a = 'an' if w[0].lower() in 'aeiou' else 'a'
    return f'{a.capitalize() if cap else a} {w}'


def sentence(picks):
    bits = []
    for slot, (ch, w) in enumerate(picks):
        bits.append([art(w, True), w, art(w), 'in ' + art(w)][slot])
    return ' '.join(bits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('progression')
    ap.add_argument('--pick', type=int, default=0, help='generate N whole scenes')
    ap.add_argument('--prompt', action='store_true', help='add an image prompt')
    a = ap.parse_args()

    seq = parse(a.progression)
    groups = [seq[i:i+4] for i in range(0, len(seq), 4)]

    print(f'\n{"-".join(seq)}')

    if not a.pick:
        for gi, grp in enumerate(groups):
            if len(groups) > 1: print(f'\n  scene {gi+1}')
            for slot, ch in enumerate(grp):
                role = ROLES[slot]
                opts = W[ch][role]
                print(f'\n  {role.upper():<7} = {ch:<3} ({SOUNDS[ch]})')
                for i in range(0, len(opts), 8):
                    print('     ' + '  '.join(opts[i:i+8]))
        print('\n  Pick one per slot. Choose words that suit the song — the '
              'picture then\n  cues twice over, from the chords and from the subject.')
        return

    for n in range(a.pick):
        scenes = []
        for grp in groups:
            picks = [(ch, random.choice(W[ch][ROLES[s]])) for s, ch in enumerate(grp)]
            scenes.append(sentence(picks))
        line = ' … then '.join(scenes)
        print(f'  {n+1}. {line}')
        if a.prompt:
            print(f'     prompt: {line}, single clear subject, centred, '
                  f'flat muted colour, simple background, no text\n')


if __name__ == '__main__':
    main()
