/* Native C fleeing-heal scenario for consumer improvement I-002 (issue408).
 *
 * Contract: borg_caution()'s heal/defend block runs only behind
 * !goal.fleeing, and goal.fleeing is cleared only on a depth change, so a
 * fleeing borg gets no healing or poison cures for the rest of the level.
 * Recorded death D0017 (seed 2993630922 turn 1094860): Dwarf Ranger CL25
 * DL21 escaped a spider pack at 7 HP with the Staff of Teleportation, read
 * Word of Recall, and then rested for Recall while poisoned with 9 Cure
 * Critical Wounds and Herbal Curing in the pack, because caution skipped
 * borg_heal() while fleeing.  This fixture reproduces that decision state
 * (wounded, poisoned, fleeing, waiting for recall, safe grid, cures in
 * pack) and requires the production borg_caution() to queue the cure
 * before the recall rest.  The controls keep the guard's other faces
 * unchanged: with real danger at the grid the new branch stays closed (the
 * only queued action is the pre-existing recall buy-time quaff, identical
 * on both builds), without fleeing the existing path heals on both builds,
 * and a healthy fleeing borg still goes straight to the recall rest.
 *
 * The recorded state values follow docs/deaths/D0017-collected: HP 7/279,
 * SP 19/42, poison about 485 turns, danger 1 after the teleport staff.
 * The old build (before the I-002 change) fails the flee-low case with the
 * recorded recall-rest keys; the controls are byte-identical across
 * builds.  Local improvement unit - never proposed upstream.
 */
#include "unit-test.h"
#include "test-utils.h"
#include "cave.h"
#include "cmd-core.h"
#include "cmds.h"
#include "game-event.h"
#include "game-world.h"
#include "init.h"
#include "mon-make.h"
#include "mon-util.h"
#include "monster.h"
#include "obj-gear.h"
#include "obj-knowledge.h"
#include "obj-make.h"
#include "obj-pile.h"
#include "obj-tval.h"
#include "obj-util.h"
#include "option.h"
#include "player.h"
#include "player-birth.h"
#include "player-calcs.h"
#include "player-spell.h"
#include "player-timed.h"
#include "player-util.h"
#include "ui-input.h"
#include "ui-menu.h"
#include "ui-term.h"
#include "borg/borg.h"
#include "borg/borg-caution.h"
#include "borg/borg-cave.h"
#include "borg/borg-cave-view.h"
#include "borg/borg-danger.h"
#include "borg/borg-fight-attack.h"
#include "borg/borg-fight-defend.h"
#include "borg/borg-flow-kill.h"
#include "borg/borg-flow.h"
#include "borg/borg-init.h"
#include "borg/borg-inventory.h"
#include "borg/borg-io.h"
#include "borg/borg-item-use.h"
#include "borg/borg-item.h"
#include "borg/borg-magic.h"
#include "borg/borg-think-dungeon-util.h"
#include "borg/borg-think.h"
#include "borg/borg-trait.h"
#include <stdio.h>
#include <stdlib.h>

static term screen;
static struct monster *giant;
static int engine_messages;

static void message(game_event_type type, game_event_data *data, void *user)
{
    const char *text = data->message.msg;
    if (!text) return;
    ++engine_messages;
    printf("ENGINE: %s\n", text);
    /* Headless message renderer; no borg turn is driven here. */
    Term_erase(0, 0, 255);
    Term_putstr(0, 0, -1, COLOUR_WHITE, text);
}

static struct object *known_item(int tval, const char *name, int number)
{
    struct object *obj = object_new();
    struct object_kind *kind = lookup_kind(tval, lookup_sval(tval, name));
    if (!kind) quit("fixture item kind missing");
    object_prep(obj, kind, 50, MAXIMISE);
    obj->number = number;
    obj->known = object_new();
    object_set_base_known(player, obj);
    object_flavor_aware(player, obj);
    inven_carry(player, obj, false, false);
    object_touch(player, obj);
    player_know_object(player, obj);
    return obj;
}

static int observe(struct monster *mon, const char *tag)
{
    mflag_on(mon->mflag, MFLAG_AWARE); update_mon(mon, cave, true);
    if (!mflag_has(mon->mflag, MFLAG_VISIBLE)) { printf("SETUPFAIL %s visible\n", tag); return 1; }
    if (!observe_kill_diff(mon->grid.y, mon->grid.x, 0, 0)) { printf("SETUPFAIL %s observe\n", tag); return 1; }
    int k = borg_grids[mon->grid.y][mon->grid.x].kill;
    if (k <= 0) { printf("SETUPFAIL %s kill_index\n", tag); return 1; }
    borg_kills[k].awake = 1;
    return 0;
}

int setup_tests(void **state)
{
    const char *profile = getenv("IM2_PROFILE");
    const char *mode = getenv("IM2_MODE");
    int spell_index = -1;
    if (!profile) return 1;
    if (!mode) mode = "flee-low";
    printf("SETUPSTEP profile\n");
    set_file_paths();
    string_free(ANGBAND_DIR_USER); ANGBAND_DIR_USER = string_make(profile);
    string_free(ANGBAND_DIR_SAVE); ANGBAND_DIR_SAVE = string_make(format("%s/save", profile));
    string_free(ANGBAND_DIR_PANIC); ANGBAND_DIR_PANIC = string_make(format("%s/panic", profile));
    string_free(ANGBAND_DIR_SCORES); ANGBAND_DIR_SCORES = string_make(format("%s/scores", profile));
    string_free(ANGBAND_DIR_ARCHIVE); ANGBAND_DIR_ARCHIVE = string_make(format("%s/archive", profile));
    if (!init_angband()) { printf("SETUPFAIL init\n"); return 1; }
    create_needed_dirs();
    Rand_quick = false; Rand_state_init(1000);
    if (!player_make_simple("Dwarf", "Ranger", "Measure")) { printf("SETUPFAIL birth\n"); return 1; }
    term_init(&screen, 255, 60, 256); Term_activate(&screen);
    angband_term[0] = &screen;
    cave = t_build_arena(40, 40); player->cave = cave_new(40, 40);
    player->depth = player->max_depth = cave->depth = player->cave->depth = 21;
    character_dungeon = true;
    for (int y = 1; y < 39; ++y) for (int x = 1; x < 39; ++x)
        sqinfo_on(square(cave, loc(x, y))->info, SQUARE_GLOW);
    known_item(TV_NATURE_BOOK, "[Lesser Charms]", 1);
    known_item(TV_POTION, "Cure Critical Wounds", 9);
    struct object *torch = known_item(TV_LIGHT, "Wooden Torch", 1);
    torch->timeout = 2000;
    inven_wield(torch, wield_slot(torch));
    player_place(cave, player, loc(11, 11));
    player_exp_gain(player, player_exp[24] * player->expfact / 100);
    player_learn_all_runes(player); calc_inventory(player);
    player->upkeep->update |= PU_BONUS | PU_TORCH | PU_HP | PU_MANA | PU_SPELLS;
    update_stuff(player);
    for (int i = 0; i < player->class->magic.total_spells; ++i) {
        if (streq(spell_by_index(player, i)->name, "Herbal Curing")) {
            spell_learn(i); spell_index = i;
        }
    }
    if (spell_index < 0) { printf("SETUPFAIL spell\n"); return 1; }
    /* Well fed: the recall wait requires it, and hunger must not add noise. */
    player->timed[TMD_FOOD] = 4000;
    /* The recorded D0017 fatal state: HP 7/279, SP 19/42, poison ~485 turns
     * (flee-full keeps the healthy state for the control). */
    if (streq(mode, "flee-full")) {
        player->chp = player->mhp; player->chp_frac = 0;
    } else {
        player->chp = 7; player->chp_frac = 0;
        player->timed[TMD_POISONED] = 485;
    }
    player->csp = 19; player->csp_frac = 0; player->msp = 42;
    borg_init();
    if (borg_init_failure || borg_cfg[BORG_CHEAT_DEATH] || OPT(player, cheat_live)) { printf("SETUPFAIL borg\n"); return 1; }
    borg_equipment(); borg_inventory(); borg_do_spell = true;
    borg.c = player->grid; borg.avoidance = player->chp; borg.ready_morgoth = 0;
    borg.escapes = 0;
    borg_cheat_spells();
    for (int y = 0; y < 40; ++y) for (int x = 0; x < 40; ++x) {
        borg_grids[y][x].feat = square(cave, loc(x, y))->feat;
        borg_grids[y][x].info |= BORG_OKAY | BORG_VIEW;
    }
    update_view(cave, player);
    /* The high-danger control parks one awake hill giant adjacent: real
     * danger at the grid must keep the flee guard closed on both builds. */
    if (streq(mode, "flee-highdanger")) {
        giant = t_add_monster(cave, loc(12, 11), "Hill giant");
        if (!giant) { printf("SETUPFAIL giant\n"); return 1; }
        if (observe(giant, "giant")) return 1;
    }
    borg_notice(true);
    /* Recorded goal state after the escape: fleeing the level, recall read. */
    borg.goal.fleeing = !streq(mode, "noflee-wounded");
    borg.goal.recalling = 1;
    borg.goal.leaving = false;
    borg.status.active = true;
    borg_update_entrypoint(true);
    event_add_handler(EVENT_MESSAGE, message, NULL);
    printf("SETUP seed=1000 mode=%s class=%s level=%d depth=%d hp=%d/%d sp=%d/%d "
           "poisoned=%d fleeing=%d recalling=%d\n",
        mode, player->class->name, player->lev, player->depth,
        player->chp, player->mhp, player->csp, player->msp,
        player->timed[TMD_POISONED] > 0, borg.goal.fleeing ? 1 : 0,
        borg.goal.recalling ? 1 : 0);
    return 0;
}

int teardown_tests(void *state)
{
    event_remove_handler(EVENT_MESSAGE, message, NULL);
    borg_update_entrypoint(false);
    cleanup_angband(); term_nuke(&screen); angband_term[0] = NULL; return 0;
}

static int drain_keys(keycode_t *keys, int max)
{
    int len = 0; keycode_t key;
    while ((key = borg_inkey(true)) != 0 && len < max) keys[len++] = key;
    return len;
}

static int scenario(void *state)
{
    const char *mode = getenv("IM2_MODE");
    keycode_t keys[64];
    int len;
    if (!mode) mode = "flee-low";
    printf("MODE %s\n", mode);

    /* One production caution decision at the recorded state. */
    bool acted = borg_caution();
    len = drain_keys(keys, 64);
    printf("DECISION acted=%d keys=%d sequence=", acted ? 1 : 0, len);
    for (int i = 0; i < len; ++i) {
        if (keys[i] == ESCAPE) printf("<Escape>"); else printf("%c", (char)keys[i]);
    }
    putchar('\n');
    /* heal: caution queued a cure/heal action instead of the recall rest
     * (Herbal Curing casts via the 'm' spell command like any borg spell).
     * rest: caution fell through to the "Resting for Recall" block. */
    int heal = acted && len > 0 && keys[0] != 'R';
    int rest = len >= 4 && keys[0] == 'R' && keys[1] == '5';
    printf("OUTCOME acted=%d heal=%d rest=%d keys=%d\n",
        acted ? 1 : 0, heal, rest, len);

    if (streq(mode, "flee-low")) {
        /* The recorded fatal decision point: safe, alone, poisoned, 7 HP,
         * cures in pack, fleeing, waiting for recall.  The borg must tend
         * the poison instead of resting over it. */
        eq(acted ? 1 : 0, 1);
        eq(heal, 1);
        eq(rest, 0);
    } else if (streq(mode, "flee-highdanger")) {
        /* Real danger at the grid: the new fleeing-heal branch stays closed
         * (pos_danger > current HP).  The queued action is the tail's
         * existing recall buy-time CCW quaff (danger > 2 * avoidance),
         * shared code on every build - never the Herbal Curing cast the
         * low-danger branch reaches through borg_heal().  Cross-build
         * byte identity of this mode's logs is checked in the evidence
         * record. */
        eq(heal, 1);
        require(keys[0] == 'q');
        eq(rest, 0);
    } else if (streq(mode, "noflee-wounded")) {
        /* Without fleeing the existing path already heals on both builds. */
        eq(heal, 1);
    } else if (streq(mode, "flee-full")) {
        /* Healthy fleeing borg: nothing to heal, straight to the rest. */
        eq(heal, 0);
        eq(rest, 1);
    }
    ok;
}
const char *suite_name = "native-c/fleeheal-408";
struct test tests[] = {{"fleeing_borg_tends_poison_at_safe_grids", scenario}, {NULL, NULL}};
