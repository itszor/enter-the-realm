#!/usr/bin/env python3
"""The translated code of Enter the Realm, and how it's made.

    images.py clean     take the Extend virus's modules out of game/!Realm (see
                        below)
    images.py decrypt   version 2: decrypt the files its protection (Merlin)
                        decrypts as it loads them (see below)
    images.py analyse   SuperSpider (analyse --full) on each machine-code
                        image -> analysis/<name>.json: the four game engines
                        (their roots the entry points in their table at &8F00),
                        !SETUP, and the modules
    images.py gen       their C translations -> recomp/gen/<name>/, and
                        recomp/gen/images.inc (game.c's tables of them)
    images.py basic     the BASIC programs, each by $SS/tools/bas2c.py --name
                        -> recomp/basic/<name>.c, and recomp/basic/programs.inc
    images.py roots LOG...   gap entries from --trace-gaps runs -> analysis/*.roots

game/ (!Realm, REALM2, REALM3: libroger's appdir, the three discs' contents
as ADFS::0.$ would hold them) comes from the original discs: $SS/tools/weave.py
extract, as recipe.json says (../build.sh). Either release: the first (the
TOSEC set) or version 2 (1992, the JASPP set: extracted/disc1v2 etc.).

The game engine is CODE, *LOADed at &8F00 by the BASIC (REALM2.X, REALM3.X,
X2, X3) and CALLed through its table of entry points at &8F04 (PASSINFO):
four builds of it, one per part of the game (REALM2.Data.CODE for disc 2's
levels; on disc 3, CODE3 outside the city, CODE in it, CODE2 in the hall). Each is translated for
&8F00 and is an overlay there (the one loaded last is the one that runs).
Version 2 has one build for disc 2's levels and the city, in two forms: for
RISC OS 3 (REALM2.Data.CODE and REALM3.CODE, the same file: it draws the
playing area's border itself, where the BASIC sets VIDC's border on RISC OS
2) and for RISC OS 2 (Data.CODE2, CODE2R); X and REALM3.X choose by
OS_Byte 129, which libroger answers as RISC OS 3.1.
"""
import hashlib
import os
import shutil
import struct
import subprocess
import sys

TOP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SS = os.environ.get('SUPERSPIDER', os.path.expanduser('~/stuff/superspider'))
SSBIN = os.path.join(SS, '_build/default/bin/main.exe')
GAME = os.path.join(TOP, 'game')
AN = os.path.join(TOP, 'analysis')
RC = os.path.join(TOP, 'recomp')



def version():
    """the release weave.py extracted: 1 (the TOSEC set) or 2 (JASPP's)"""
    v2 = [os.path.isdir(os.path.join(TOP, 'extracted', 'disc%dv2' % k)) for k in (1, 2, 3)]
    if any(v2) and not all(v2):
        sys.exit('images.py: the discs are of both releases (extracted/): give all three of one')
    return 2 if all(v2) else 1


# (name, path in game/, the RISC OS names libroger knows it by when loaded)
ENGINES = {1: [('data_code', 'REALM2/Data/CODE', ['Data.CODE']),    # disc 2: snow, forest, caves, plains (X)
               ('code', 'REALM3/CODE', ['REALM3.CODE']),            # disc 3: the city (REALM3.X)
               ('code2', 'REALM3/CODE2', ['CODE2']),                # the hall (X2)
               ('code3', 'REALM3/CODE3', ['CODE3'])],               # outside the city (X3)
           2: [('v2_code', 'REALM3/CODE', ['Data.CODE', 'REALM3.CODE']),   # RISC OS 3: disc 2, the city
               ('v2_code_ro2', 'REALM3/CODE2R', ['Data.CODE2', 'CODE2R']),  # RISC OS 2: the same
               ('v2_code2', 'REALM3/CODE2', ['REALM3.CODE2']),     # the hall (X2)
               ('v2_code3', 'REALM3/CODE3', ['CODE3'])]}[version()]   # outside the city (X3)
ENGINE_BASE = 0x8F00
# PASSINFO's words that are code: !8 the start (PRESS FIRE), !12 go on after
# a building, !16 a VIDC poke, !20, !28, !32, !36 the pictures' and the
# palettes' routines (the BASIC CALLs them); the others are data
CALLED = (2, 3, 4, 5, 7, 8, 9)

SETUP = ('setup', '!Realm/!SETUP', 0x8000)   # the utility !Run runs first (dynamic areas)

# the modules: ExSound (the intro's music, *RMLoaded by QUICK; *RMClear
# kills it), and the voices the Loader *RMRuns, each in its own 64K of RMA
MODULES = ['ExSound', 'RAIN', 'SWORD', 'BOUNCE', 'PICKUP', 'DOOR', 'EXPLOS', 'DEATH', 'OUCH',
           'SPELL', 'BARK', 'GETREADY', 'GAMEOVER', 'DRUMS', 'DRUMSE']
MOD_BASE = 0x1840000

# the BASIC programs: (C name, path in game/, the RISC OS name CHAIN finds
# it by: its last components)
PROGRAMS = [('quick', '!Realm/QUICK', '!Realm.QUICK'),
            ('startup', '!Realm/Startup', '!Realm.STARTUP'),
            ('loader', '!Realm/Loader', '!Realm.LOADER'),
            ('starter', 'REALM2/Starter', 'REALM2.STARTER'),
            ('defkeys', 'REALM2/DefKeys', 'REALM2.DEFKEYS'),
            ('x', 'REALM2/X', 'REALM2.X'),
            ('gameover', 'REALM2/GAMEOVER', 'REALM2.GAMEOVER'),
            ('snow', 'REALM2/SNOW/CODECX', 'REALM2.SNOW.CODECX'),
            ('forest', 'REALM2/FOREST/CODECX', 'REALM2.FOREST.CODECX'),
            ('caves', 'REALM2/CAVES/CODECX', 'REALM2.CAVES.CODECX'),
            ('plains', 'REALM2/PLAINS/CODECX', 'REALM2.PLAINS.CODECX'),
            ('x3a', 'REALM3/X', 'REALM3.X'),
            ('x2', 'REALM3/X2', 'REALM3.X2'),
            ('x3', 'REALM3/X3', 'REALM3.X3'),
            ('outside', 'REALM3/OUTSIDE/CODECX', 'REALM3.OUTSIDE.CODECX'),
            ('hall', 'REALM3/HALL/CODECX', 'REALM3.HALL.CODECX'),
            ('city', 'REALM3/CITY/CODECX', 'REALM3.CITY.CODECX'),
            ('finale', 'REALM3/FINALE/LOADER', 'REALM3.FINALE.LOADER')]


def find(path, top=GAME):
    """a RISC OS file in game/ (or top): any case, any ,load-exec suffix"""
    d = top
    for part in path.split('/'):
        for f in os.listdir(d):
            if f.split(',')[0].lower() == part.lower():
                d = os.path.join(d, f)
                break
        else:
            raise FileNotFoundError(os.path.join(d, part))
    return d


def rel(p):
    return os.path.relpath(p, RC)


def modules():
    """(name, file, base)"""
    return [(m.lower(), find('!Realm/MODS/' + m), MOD_BASE + k * 0x10000) for k, m in enumerate(MODULES)]


def engine_roots(path):
    d = open(path, 'rb').read()
    return sorted({struct.unpack_from('<I', d, 4 * k)[0] for k in CALLED})


def run(cmd, **kw):
    print('+', ' '.join(cmd))
    subprocess.run(cmd, check=True, **kw)


# --- clean, analyse, gen, basic, roots
# The TOSEC dump's disc 1 carries two viruses of the time, neither part of
# the game (and neither run here: libroger runs no !Boot files), taken out
# of game/ by `clean`:
# - Extend 1.56 (1989): five copies of a 940-byte module titled Extend
#   (OSextend, CheckMod, CodeRM, ExtendRM, MonitorRM) in !Realm, and a line
#   "RMEnsure Extend 0 RMRun <Obey$Dir>.OSextend" (and a few bytes after
#   it) added to !Realm.!Boot;
# - "Icon" (QEGS Wakefield, 1990, by its own comments): a BASIC program
#   named !SOUNDS.Icon, typed as a sprite, and two lines added to
#   !SOUNDS.!Boot to run it (disc 3's !SOUNDS is clean).
def is_extend(path):
    """a copy of the Extend virus: a 940-byte module titled Extend"""
    d = open(path, 'rb').read()
    if len(d) != 940:
        return False
    t = struct.unpack_from('<I', d, 16)[0]
    return d[t:t + 7] == b'Extend\0'


def is_icon_virus(path):
    """!SOUNDS.Icon as the Icon virus left it: a BASIC program, not a sprite"""
    d = open(path, 'rb').read()
    return d[:1] == b'\r' and b'virus' in d


def clean():
    app = find('!Realm')
    for f in sorted(os.listdir(app)):
        p = os.path.join(app, f)
        if os.path.isfile(p) and is_extend(p):
            print('  removing %s (the Extend virus)' % f)
            os.remove(p)
    try:                                    # (version 2's disc has no !Boot, and is clean)
        boot = find('!Realm/!Boot')
    except FileNotFoundError:
        boot = None
    d = open(boot, 'rb').read() if boot else b''
    k = d.find(b'\rRMEnsure Extend 0 RMRun <Obey$Dir>.OSextend')
    if k >= 0:
        print('  !Realm.!Boot: the Extend virus\'s line removed')
        open(boot, 'wb').write(d[:k + 1])
    try:
        icon = find('!SOUNDS/Icon')
    except FileNotFoundError:
        return
    if is_icon_virus(icon):
        print('  removing !SOUNDS.Icon (the Icon virus)')
        os.remove(icon)
        boot = find('!SOUNDS/!Boot')
        d = open(boot, 'rb').read()
        for line in (b'wimpslot -min 16k -max 16k\n', b'BASIC -quit <Obey$Dir>.Icon\n'):
            d = d.replace(line, b'')
        open(boot, 'wb').write(d.rstrip(b'\n') + b'\n')


def roots_file(name):
    return os.path.join(AN, name + '.roots')


# --- decrypt
# Version 2's protection, a module titled Merlin, is in !Realm.MODS.Wand (a
# utility, encrypted in layers: each decrypts the next). QUICK *RUNs it: it
# reads sector 1 of track 78, side 1 (ADFS_DiscOp, disc address &C4800),
# which has a bad CRC on the disc (no error: "Go Away you 'Orrible little
# worm"), keeps the data it reads all the same, and inserts Merlin. Merlin
# claims FileV, FindV, GBPBV, BPutV and ArgsV, and decrypts what is loaded
# from the disc: each byte XORed with that sector's (byte k of a file with
# byte k MOD 1024). CLIV it claims to refuse commands that would look at
# the decrypted data (*Save, *Memory, ...); its command *<CHR$160> (shown
# blank: it redefines character 160 as blank) loads the intro's pictures,
# one each time, as the first release's QUICK *Loaded them. LOADER, the
# last decrypted file, *RMKills it. Here the files are decrypted into
# game/ (from extracted/disc1v2) instead (Wand, QUICK's *<CHR$160> and *RMKill Merlin: game.c); the
# sector comes from disc 1's image, which weave.py keeps (recipe.json:
# "raw"). LOGO2 and FONT1, which RISC OS 2 loads in place of LOGO and FONT,
# aren't encrypted.
PROTECTED = ['!Realm/Startup', '!Realm/Loader', '!Realm/Intro/INTROPAL', '!Realm/Intro/HORSE',
             '!Realm/Intro/TITLE', '!Realm/Intro/PANEL1', '!Realm/Intro/PANEL2', '!Realm/Intro/LOGO',
             '!Realm/Sprites/FONT']
KEY_ADDR = 0xC4800
KEY_SHA = 'fd42b22cfca96b7df2c508e30fdb9280c173787a68b362460df8c79a4c9df4c9'


def protection_key():
    """the protection sector, from disc 1's image (extracted/disc1v2.*)"""
    sys.path.insert(0, os.path.join(SS, 'tools'))
    import hfe
    import jfd
    for ext, decode in (('.jfd', lambda p: jfd.decode(p)[0]), ('.hfe', lambda p: hfe.decode(p)[0]),
                        ('.img', lambda p: open(p, 'rb').read())):
        p = os.path.join(TOP, 'extracted', 'disc1v2' + ext)
        if os.path.exists(p):
            key = decode(p)[KEY_ADDR:KEY_ADDR + 1024]
            if hashlib.sha256(key).hexdigest() != KEY_SHA:
                sys.exit('images.py: %s: the protection sector at &%X isn\'t the one expected' % (p, KEY_ADDR))
            return key
    sys.exit('images.py: version 2 needs disc 1\'s image (extracted/disc1v2.jfd, .hfe or .img)')


def decrypt():
    if version() < 2:
        return
    key = protection_key()
    for path in PROTECTED:
        f = find(path)
        d = open(find(path, os.path.join(TOP, 'extracted', 'disc1v2')), 'rb').read()
        d = bytes(c ^ key[k & 1023] for k, c in enumerate(d))
        if f.split(',')[1].startswith('fffffb') and d[:1] != b'\r':
            sys.exit('images.py: %s isn\'t BASIC once decrypted' % path)
        print('  decrypting %s' % path)
        open(f, 'wb').write(d)


def analyse():
    os.makedirs(AN, exist_ok=True)
    run(['dune', 'build'], cwd=SS)
    for name, path, _ in ENGINES:
        f = find(path)
        calls = os.path.join(AN, name + '.calls')
        with open(calls, 'w') as o:
            o.write('# PASSINFO: the entry points the BASIC CALLs (images.py engine_roots)\n')
            o.writelines('%x\n' % a for a in engine_roots(f))
            if os.path.exists(roots_file(name)):
                o.write(open(roots_file(name)).read())
        # (from the start entry: the table at the base isn't code)
        start = struct.unpack_from('<I', open(f, 'rb').read(), 8)[0]
        run([SSBIN, 'analyse', f, '%x' % ENGINE_BASE, '--exec', '%x' % start, '--full', '--roots', calls,
             '-o', os.path.join(AN, name + '.json')])
    name, path, base = SETUP
    run([SSBIN, 'analyse', find(path), '%x' % base, '--full', '-o', os.path.join(AN, name + '.json')])
    for name, f, base in modules():
        r = roots_file(name)
        run([SSBIN, 'analyse', f, '%x' % base, '--module', '--full', '-o', os.path.join(AN, name + '.json')] +
            (['--roots', r] if os.path.exists(r) else []))


def gen():
    shutil.rmtree(os.path.join(RC, 'gen'), ignore_errors=True)
    images = [(n, find(p), ENGINE_BASE) for n, p, _ in ENGINES] + [(SETUP[0], find(SETUP[1]), SETUP[2])] + modules()
    for k, (name, f, base) in enumerate(images):
        run([SSBIN, 'gen', f, '%x' % base, os.path.join(AN, name + '.json'), '--c', os.path.join(RC, 'gen', name),
             '--prefix', 'I%d' % k, '--tabprefix', 'recomp_' + name, '--covtag', chr(ord('a') + k)] +
            ([] if k < len(ENGINES) else ['--files', '1']))
    with open(os.path.join(RC, 'gen', 'images.inc'), 'w') as o:
        o.write('/* generated by ../tools/images.py - the translated images, for game.c */\n')
        for name, _, _ in images:
            o.write('extern const struct roger_image recomp_%s_image;\n' % name)
        o.write('#define SETUP_PATH "%s"\n' % rel(find(SETUP[1])))
        o.write('/* the game engines: overlays at &%X, by the name each is *LOADed by */\n' % ENGINE_BASE)
        o.write('static const struct roger_program programs[] = {\n')
        for name, _, leaves in ENGINES:
            for leaf in leaves:
                o.write('    {"%s", &recomp_%s_image, 1, 0},\n' % (leaf, name))
        o.write('    {NULL, NULL, 0, 0}};\n')
        o.write('/* the modules, loaded when the BASIC asks for them */\n')
        o.write('static const struct roger_module modules[] = {\n')
        for name, f, _ in modules():
            o.write('    {"%s", &recomp_%s_image, 1},\n' % (rel(f), name))
        o.write('    {NULL, NULL, 0}};\n')


def basic():
    d = os.path.join(RC, 'basic')
    os.makedirs(d, exist_ok=True)
    for name, path, riscos in PROGRAMS:
        run([sys.executable, '-I', os.path.join(SS, 'tools/bas2c.py'), '--name', name, '--riscos', riscos,
             find(path), os.path.join(d, name + '.c')])
    with open(os.path.join(d, 'programs.inc'), 'w') as o:
        o.write('/* generated by ../tools/images.py - the BASIC programs, for game.c */\n')
        for name, _, _ in PROGRAMS:
            o.write('extern const struct bas_program bas_prog_%s;\n' % name)
        o.write('static const struct bas_program *const bas_programs[] = {\n')
        for name, _, riscos in PROGRAMS:
            o.write('    &bas_prog_%s,      /* %s */\n' % (name, riscos))
        o.write('    NULL};\n')


def roots(logs):
    for name, path, _ in ENGINES:
        run([sys.executable, os.path.join(SS, 'tools/gap_roots.py'), find(path), '%x' % ENGINE_BASE,
             roots_file(name)] + logs)
    for name, f, base in modules():
        run([sys.executable, os.path.join(SS, 'tools/gap_roots.py'), f, '%x' % base, roots_file(name)] + logs)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == 'roots':
        roots(sys.argv[2:])
    else:
        for step in sys.argv[1:]:
            {'clean': clean, 'decrypt': decrypt, 'analyse': analyse, 'gen': gen, 'basic': basic}[step]()
