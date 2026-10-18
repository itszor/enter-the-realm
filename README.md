Enter the Realm (The Fourth Dimension, 1991) - static recompilation
==================================================================

A recipe: this repository holds no game data. It rebuilds the game as a
native executable from your own copy of the three discs, recognised by
content (recipe.json), so it can be shared without distributing the game.

    ./build.sh "Enter the Realm (1991)(The Fourth Dimension)(Disk 1 of 3).adf" \
               "Enter the Realm (1991)(The Fourth Dimension)(Disk 2 of 3).adf" \
               "Enter the Realm (1991)(The Fourth Dimension)(Disk 3 of 3).adf"
    cd recomp && ./enterrealm

or from version 2 (1992), as JASPP's archive has it (.jfd images, ADFFS's):

    ./build.sh "Enter The Realm (1991) (The Fourth Dimension) F1013400.zip"

build.sh runs recipe.json's steps with SuperSpider's tools/weave.py
(~/stuff/superspider, or $SUPERSPIDER; $SS below): it finds the three discs
among the inputs, extracts them, takes out two viruses (below), analyses
and translates the machine code, translates the BASIC, and links it all
with libroger (~/stuff/libroger, or make ROGER=...). It takes about two
minutes. Needs python3, OCaml/dune, gcc and SDL3.

Inputs: the TOSEC set's three disc images (ADFS E format, 800K), or a zip
holding them; or version 2's three, JASPP's F1013401-3.jfd (disc 1 ADFS D,
discs 2 and 3 E), or its zip. weave.py reads .jfd ($SS/tools/jfd.py) and
takes the three discs of either release (recipe.json: each disc's
"alternatives"), but not a mixture.

What it makes:

    extracted/disc1-3        $SS/tools/adf_extract.py's output, via weave.py
    game/                    !Realm, !SOUNDS (disc 1), REALM2, REALM3: the discs as
                             ADFS::0.$ would hold them, libroger's appdir
    analysis/*.json          SuperSpider's analyses (the four game engines,
                             !SETUP, the fifteen modules)
    recomp/gen/              their C translations
    recomp/basic/            the eighteen BASIC programs' C (bas2c.py)
    recomp/enterrealm        the game
    basic/                   make -C recomp listings: the BASIC as text, to read

Committed: recipe.json, build.sh, tools/images.py, recomp/ (Makefile,
game.c), this file.

How the game is put together
----------------------------

!Run sets a 760K WimpSlot, runs !SETUP (a 128-byte utility: the dynamic
areas - 192K of RMA, one 80K screen, 16K of sprites), *RMClears and starts
BASIC on !Realm.QUICK. From then on it is BBC BASIC, eighteen programs
that CHAIN one another:

    QUICK                    the title sequence (ExSound's music, the logo, the horse)
    STARTUP, LOADER          the prophecy; the sound modules, sprites and keys
    REALM2.STARTER           the title scroll and the high scores; the story so far
    REALM2.DEFKEYS           redefining the keys (R at the title)
    <level>.CODECX           a level's loader: its pictures (run-length coded),
                             its map, monsters and palette, at fixed addresses
    REALM2.X, REALM3.X3, X, X2   the levels: *LOAD the engine (CODE) and CALL it;
                             the buildings (the wizard's tower, the tavern - a
                             mouse-driven menu in BASIC - the church, the tower)
                             and the story between levels
    REALM2.GAMEOVER          the high score table (saved: savedata/REALM2/DATA)
    REALM3.FINALE.LOADER     the end

Disc 2's levels are the snow, the forest, the caves and the plains of
Chrelos; disc 3's are outside the city, the city and the king's hall. The
programs keep their state in memory at fixed addresses (&10900: the score,
lives, energy, weapons; &10924: the keys) and in A%-Z%.

- recomp/basic/: each program translated by $SS/tools/bas2c.py --name, on
  SuperSpider's BASIC runtime ($SS/runtime/basic_runtime.c). bas_run (the
  runtime) runs one program at a time at PAGE, its heap from its TOP, and
  CHAIN starts the program it names afresh (A%-Z% and PAGE kept: STARTUP
  sets PAGE=&A7000, above the levels' data, for all the programs after it).
  bas2c learnt CHAIN, PAGE=, MID$()=, ON ERROR OFF, VPOS, GOTOs between a
  PROC and the main program (QUICK's PROCP leaves itself for the main
  program; DefKeys' main program GOTOs lines after PROCK's ENDPROC) and a DEF
  line inside a loop (DefKeys' FNkey), as BASIC runs them.
- The programs assemble small routines of their own - copies, two
  run-length decoders, a nibble-run decoder, the joystick test - and CALL
  them: bas2c translates the assembler ($SS/tools/basasm.py) into C that
  assembles at run time, at P%, as BASIC's would. The routines, made as the
  game runs, are interpreted (interpret_gaps).
- The engine: four builds of CODE at &8F00, entered through the table of
  routines at its start (PASSINFO: start a level, go on after a building,
  poke VIDC, the pictures' and palettes' routines). Each is translated
  (tools/images.py: from its start entry; its table's routines the roots)
  and is an overlay at &8F00 - libroger runs the one loaded last; two of the
  files are both called CODE (REALM2.Data.CODE, REALM3.CODE), told apart by
  their last two components. Everything translates: headless runs through
  every level, the buildings, the high scores and the finale interpret
  nothing of it. One instruction, &E3A33077 (mov r3,#&77 with a non-zero
  Rn, which an ARM2 ignores), needed SuperSpider to take such encodings as
  code when ordinary code runs on into them.
- !SETUP is the program libroger loads (at &8000); game.c's init runs it,
  then the rest of !Run.
- The sound: ExSound 3.30 (Sound Extension) plays the title music, its
  instruments from disc 1's !SOUNDS (Sounds$Dir, as !SOUNDS.!Boot sets it);
  *RMClear kills it. Thirteen voice generator modules (RAIN, SWORD, ...,
  DRUMS) are *RMRun by running the files; the engine attaches its channels
  to them by number (10-22, as RISC OS 3.1 numbers them after its ROM's
  nine) and gives Sound_Control 16-bit amplitudes (&FFF1).

Version 2
---------

The second release (1992; !RealmInfo: "Enter the Realm Version 2.0"), the
one JASPP preserved, runs in 1MB (an A3000 with 760K for the game), on
RISC OS 2 and 3, and fixes loading and saving. What changed:

- RISC OS 3: the BASIC reads OS_Byte 129. On RISC OS 3 (> 162) it loads
  LOGO and FONT, and the engine REALM2.Data.CODE (REALM3.CODE is the same
  file), which draws the playing area's border itself every frame; on
  RISC OS 2, LOGO2, FONT1 and Data.CODE2 (= REALM3.CODE2R), and the BASIC
  sets VIDC's border as the first release did. libroger answers as RISC
  OS 3.1, so the RISC OS 3 forms run; both engines are translated.
- A cheat mode: Shift and Ctrl held as the title page is left (STARTER's
  Q%, the engine's ?&8F01).
- The disc prompts retry on an error; saving the keys or the high scores
  to a protected disc says so and goes on.
- Copy protection, Merlin (tools/images.py, decrypt): the files of disc
  1's intro (STARTUP, LOADER, the intro's pictures, FONT) are encrypted,
  each byte XORed with a sector on track 78 that has a bad CRC; MODS.Wand
  checks the CRC error and installs Merlin, which decrypts files as they
  are loaded, until LOADER kills it. Here `images.py decrypt` decrypts
  them into game/ from disc 1's image (kept: recipe.json's "raw"), and
  game.c stands in for Wand, Merlin's command (*<CHR$160>: QUICK's five
  loads of the intro's pictures) and the *RMKill.
- Disc 1 has no viruses.

The viruses
-----------

The TOSEC dump's (the first release's) disc 1 carries two viruses of the time. Neither is part of
the game and neither runs here (libroger runs no !Boot files), but
`images.py clean` takes them out of game/ so they aren't copied on:

- Extend 1.56 (1989): five copies of a 940-byte module titled Extend
  (!Realm.OSextend, CheckMod, CodeRM, ExtendRM, MonitorRM) and the line
  !Realm.!Boot runs it with ("RMEnsure Extend 0 RMRun <Obey$Dir>.OSextend").
- "Icon" (QEGS Wakefield, 1990, by its own comments): a BASIC program called
  !SOUNDS.Icon, typed as a sprite, and the two lines it added to
  !SOUNDS.!Boot. Disc 3's !SOUNDS is clean.

extracted/ keeps the discs as they are.

Speed and controls
------------------

The levels aren't paced: each frame takes as long as the machine takes to
draw it. game.c sets libroger's CPU speed to an 8MHz ARM2's, 4.5 MIPS
(--mips=N to change it, --mips=0 for flat out). The BASIC's own pauses are
timed by TIME and WAIT, as on the original.

The keys (the disc's KeyDefs; R at the title page redefines them, and the
new ones can be saved): Z left, X right, ' jump, / crouch, Return fire,
Space go into a building, P pause. Space also answers the "insert disc"
prompts - every disc is already there. In the tavern: the mouse.

A game controller is the joystick the game reads itself (Keith Martin's
interface, The Fourth Dimension's: its port at &33A0004, which libroger now
gives the first controller's lines): the stick or D-pad moves, jumps and
crouches, A or B fire; X is Space, Y is P.

    --level=NAME     start at a level, from the title page: snow forest caves
                     plains outside hall city finale

A headless scenario (Space: the title sequence skipped, disc 2
"inserted", the title page left and the story skipped; then fire, and a
walk to the right in the snow; the screenshots as screenshot-N.bmp):

    ./enterrealm --limit=1.5e8 --full-os --script=20000:key:99:300,\
    28000:key:99:300,36000:key:99:100,40000:shot,46000:key:74:300,\
    50000:shot,52000:key:67:8000,60000:shot,66000:shot

Version 2 waits for one more Space (STARTER) and starts the level later:

    ./enterrealm --limit=3e8 --full-os --script=20000:key:99:300,\
    28000:key:99:300,36000:key:99:100,44000:key:99:100,50000:shot,\
    52000:key:74:300,56000:shot,58000:key:74:300,60000:shot,\
    62000:key:67:8000,66000:shot,70000:shot

Not done
--------

- The joystick's second port (the game reads only the first).
- A copy saved to the discs (keys, high scores) goes to recomp/savedata,
  libroger's save directory, and is read back from there.
