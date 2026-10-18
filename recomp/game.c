/* Enter the Realm (The Fourth Dimension, 1991): what libroger needs to
 * know about the game.
 *
 * !Run: WimpSlot 760K, then *Run !Setup (a utility: the dynamic areas -
 * 192K of RMA, 80K of screen, 16K of sprites, nothing else), *RMClear,
 * and BASIC !Realm.QUICK. From there it is BASIC all the way: eighteen
 * programs that CHAIN one another (the intro, the story so far, the
 * loader, the high scores, a loader for each level, and the X programs
 * that run the levels), each translated by SuperSpider's tools/bas2c.py
 * (basic/, programs.inc) and run by its BASIC runtime (bas_run, bas_chain).
 * They assemble little routines of their own (copies, run-length decoders,
 * a joystick test) and CALL them - interpreted, as code made at run time -
 * and *LOAD the game engine (CODE: four builds of it, ../tools/images.py)
 * at &8F00 and CALL it through its table there.
 *
 * The three discs are merged in ../game as ADFS::0.$ would hold them
 * (!Realm and !SOUNDS, REALM2, REALM3), so each "INSERT REALM DISC n" finds
 * its disc there (after Space, as on the original). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "basic_runtime.h"

#include "gen/images.inc"       /* the engines (programs), !SETUP, the modules */
#include "basic/programs.inc"   /* bas_programs */

/* the BASIC runtime ($SS/runtime/basic_runtime.c): PAGE as BASIC starts
 * with it (STARTUP sets &A7000 for the programs after it, above the
 * game's data); each program's heap starts at its TOP (bas_run) */
int32_t bas_page = 0x8F00;
uint32_t bas_lomem;

/* every name is ADFS::0.$.something: the discs, merged in ../game */
static const char *const prefixes[] = {"ADFS::0.$.", "ADFS::$.", ":0.$.", NULL};
/* Obey$Dir as !Run leaves it; Sounds$Dir as !SOUNDS.!Boot sets it when the
 * Filer first sees disc 1 (ExSound's tunes find their instruments there) */
static const char *const variables[] = {"Obey$Dir", "ADFS::0.$.!Realm", "Sounds$Dir", "ADFS::0.$.!SOUNDS", NULL};

/* (bas2c translates every assembler statement the programs have: none
 * comes here) */
void bas_asm(const char *text) { fprintf(stderr, "bas_asm: not handled: %s\n", text); }

/* --level=NAME: the game starts at a level (its loader, NAME.CODECX), not
 * in the snow: STARTER CHAINs it in place of SNOW.CODECX */
static const char *const levels[] = {"snow", "forest", "caves", "plains", "outside", "hall", "city", "finale", NULL};
static const char *level;

static int game_arg(const char *a)
{
    if (strncmp(a, "--level=", 8)) return 0;
    for (int k = 0; levels[k]; k++)
        if (!strcasecmp(a + 8, levels[k])) { level = levels[k]; return 1; }
    fprintf(stderr, "--level: one of snow forest caves plains outside hall city finale\n");
    exit(2);
}

/* Version 2's protection, Merlin (../tools/images.py: decrypt), whose
 * files are decrypted in ../game already: QUICK's *RUN of MODS.WAND (the
 * disc's check, and Merlin), its five *<CHR$160>s (Merlin's command, each
 * loading the next of the intro's pictures, as the first release's QUICK
 * *Loaded them) and LOADER's *RMKill Merlin */
static const char *const intro[] = {"INTROPAL 20000", "HORSE 21000", "TITLE 31000", "PANEL1 6C000",
                                    "PANEL2 80000", NULL};
static int intro_next;

static int game_cli(const char *c)
{
    while (*c == ' ' || *c == '*') c++;
    if (!strcasecmp(c, "RUN <Obey$Dir>.MODS.WAND") || !strcasecmp(c, "RMKILL Merlin")) return 1;
    if ((unsigned char)c[0] == 0xA0 && !c[1]) {
        char cmd[64];
        if (!intro[intro_next]) return 1;
        snprintf(cmd, sizeof cmd, "LOAD <Obey$Dir>.INTRO.%s", intro[intro_next++]);
        roger_cli(cmd);
        return 1;
    }
    return 0;
}

static const struct bas_program *chain(const char *name)
{
    size_t l = strlen(name);
    if (!level || l < 11 || strcasecmp(name + l - 11, "SNOW.CODECX")) return NULL;
    for (int k = 0; bas_programs[k]; k++) {
        const char *n = bas_programs[k]->name, *d = strchr(n, '.');
        if (d && !strncasecmp(d + 1, level, strlen(level)) && d[1 + strlen(level)] == '.') {
            level = NULL;                        /* (only the first time) */
            return bas_programs[k];
        }
    }
    return NULL;
}

/* !Run, after the WimpSlot */
static void init(void)
{
    bas_chain_hook = chain;
    bas_cli = game_cli;
    R[13] = 0x8F00;                             /* !Setup, a utility: at &8000 here */
    roger_call_program(0x8000, ROGER_HANDLER_RET);
    roger_cli("RMCLEAR");
    roger_cli("SET Disc2 <ADFS::0.$.REALM2>");
    roger_cli("SET Disc3 <ADFS::0.$.REALM3>");
    bas_run(bas_programs, &bas_prog_quick);     /* BASIC <Obey$Dir>.QUICK */
}

static struct roger_config config = {
    .title = "Enter the Realm (recompiled)",
    /* Keith Martin's joystick interface, which the game reads itself (the
     * byte at &33A0004: libroger's, from a controller); the stick moves,
     * jumps (up) and crouches (down), A or B fire. X is Space (go into a
     * building, and the "press Space" prompts), Y is P (pause) */
    .joystick = ROGER_JOY_KM,
    .pad_map = "x=Space,y=P,start=Space,back=Escape",
    .image_path = SETUP_PATH,
    .image = &recomp_setup_image,
    .programs = programs,
    .modules = modules,
    .appdir = "../game",
    .dir_prefixes = prefixes,
    .variables = variables,
    .initial_mode = 12,
    .wimpslot = 760 * 1024,
    .screen_size = 0x14000,                      /* !Setup: 80K, one mode 13 screen */
    /* the BASIC's own routines, assembled as it runs, are interpreted */
    .interpret_gaps = 1,
    /* The levels aren't paced: each frame takes as long as the machine
     * takes to draw it. An 8MHz ARM2's speed; --mips=N to change it, 0 for
     * flat out */
    .mips = 4.5,
    .init = init,
    .arg = game_arg,
    .usage = "  --level=NAME      start at a level: snow forest caves plains (disc 2),\n"
             "                    outside hall city finale (disc 3)\n",
};

int main(int argc, char **argv) { roger_main(argc, argv, &config); }
