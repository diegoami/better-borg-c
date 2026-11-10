/* Native C starting-purchase scenario for consumer improvement I-003
 * (issue410).
 *
 * Contract: borg_think_shop_buy_useful()'s power valuation rewards the
 * first phase door (+50000) and armour, gives later phase doors +500
 * (suppressed entirely for munchkin-start classes below the munchkin
 * level), rewards no cure potion below CL10 and no carried recall below
 * CL8 - so starting gold went to armour with one phase door, no cure
 * potions and the recall stored (recorded D0013-D0019 first visits;
 * ledgers on issue410).  The improvement reserves gold while
 * BI_MAXCLEVEL <= 7: buy the cheapest affordable deficit toward 4 phase
 * doors + 3 cure potions first, and suppress every other purchase in this
 * function while a deficit remains.  Urgent states (no food, no light,
 * cut, poisoned) and the reserve-met case keep the old behavior.
 *
 * The fixture stocks the real game stores (store_carry) and runs
 * borg_notice_store(), so the wares and their costs are exactly what the
 * production chooser reads.  Modes:
 *   pd-second        1 phase door held, 357 gold, PD + armour + CLW in
 *                    stock - before build buys the armour, after build
 *                    buys the second phase door (cheapest deficit);
 *   clw-deficit      4 phase doors held, 200 gold - before build buys
 *                    armour, after build buys the CLW deficit;
 *   reserve-complete 4 phase doors + 3 CLW held - the reserve pass is
 *                    inert, both builds resume the valuation (its own
 *                    winner, e.g. rations), logs byte-identical;
 *   urgent-poisoned  poisoned: the gate is skipped, both builds use the
 *                    existing poisoned path (alchemy shop), logs
 *                    byte-identical.
 * The old build fails pd-second and clw-deficit; the controls are
 * byte-identical across builds.  Local improvement unit - never proposed
 * upstream.
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
#include "store.h"
#include "ui-input.h"
#include "ui-menu.h"
#include "ui-term.h"
#include "borg/borg.h"
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
#include "borg/borg-item-val.h"
#include "borg/borg-store-buy.h"
#include "borg/borg-think-dungeon-util.h"
#include "borg/borg-think.h"
#include "borg/borg-trait.h"
#include <stdio.h>
#include <stdlib.h>

static term screen;
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

/* Stock a real game store; borg_notice_store() then shows it to the
 * chooser exactly as in play, with the computed store price. */
static int stock_ware(int store_num, int tval, const char *name, int number)
{
    struct object *obj = object_new();
    struct object_kind *kind = lookup_kind(tval, lookup_sval(tval, name));
    if (!kind) { printf("SETUPFAIL ware kind %s\n", name); return 1; }
    object_prep(obj, kind, 0, MAXIMISE);
    obj->number = number;
    obj->known = object_new();
    object_set_base_known(player, obj);
    object_flavor_aware(player, obj);
    if (!store_carry(&stores[store_num], obj, true)) {
        printf("SETUPFAIL carry %s\n", name);
        return 1;
    }
    return 0;
}

int setup_tests(void **state)
{
    const char *profile = getenv("SB410_PROFILE");
    const char *mode = getenv("SB410_MODE");
    if (!profile) return 1;
    if (!mode) mode = "pd-second";
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
    if (!player_make_simple("Human", "Necromancer", "Measure")) { printf("SETUPFAIL birth\n"); return 1; }
    term_init(&screen, 255, 60, 256); Term_activate(&screen);
    angband_term[0] = &screen;
    cave = t_build_arena(40, 40); player->cave = cave_new(40, 40);
    player->depth = player->max_depth = cave->depth = player->cave->depth = 1;
    character_dungeon = true;
    for (int y = 1; y < 39; ++y) for (int x = 1; x < 39; ++x)
        sqinfo_on(square(cave, loc(x, y))->info, SQUARE_GLOW);
    struct object *torch = known_item(TV_LIGHT, "Wooden Torch", 1);
    torch->timeout = 2000;
    inven_wield(torch, wield_slot(torch));
    known_item(TV_FOOD, "Ration of Food", 2);

    /* Carried stock per mode (counts that feed BI_APHASE/BI_ACLW). */
    if (streq(mode, "pd-second") || streq(mode, "urgent-poisoned")
        || streq(mode, "homesell-guard")) {
        known_item(TV_SCROLL, "Phase Door", 1);
    } else if (streq(mode, "clw-deficit") || streq(mode, "reserve-complete")) {
        known_item(TV_SCROLL, "Phase Door", 4);
    }
    if (streq(mode, "reserve-complete")) {
        known_item(TV_POTION, "Cure Light Wounds", 3);
    }

    player_place(cave, player, loc(11, 11));
    player->upkeep->update |= PU_BONUS | PU_TORCH | PU_HP | PU_MANA | PU_SPELLS;
    update_stuff(player);
    player_learn_all_runes(player); calc_inventory(player);
    player->upkeep->update |= PU_BONUS | PU_HP | PU_MANA | PU_SPELLS;
    update_stuff(player);
    /* The recorded first-visit gold and the urgent control's poison. */
    player->au = 357;
    if (streq(mode, "clw-deficit") || streq(mode, "reserve-complete"))
        player->au = 200;
    if (streq(mode, "urgent-poisoned"))
        player->timed[TMD_POISONED] = 100;

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
    borg_notice(true);

    /* Stock the real stores: general (0) carries the phase doors and the
     * tempting armour, temple (3) the CLW, alchemy (4) cure poison. */
    if (stock_ware(0, TV_SCROLL, "Phase Door", 6)) return 1;
    if (stock_ware(0, TV_HARD_ARMOR, "Chain Mail", 1)) return 1;
    if (stock_ware(3, TV_POTION, "Cure Light Wounds", 6)) return 1;
    if (stock_ware(4, TV_POTION, "Neutralize Poison", 4)) return 1;
    borg_notice_store();

    borg.goal.shop = -1;
    borg.goal.ware = -1;
    borg.status.active = true;
    borg_update_entrypoint(true);
    event_add_handler(EVENT_MESSAGE, message, NULL);
    printf("SETUP seed=1000 mode=%s class=%s level=%d maxlevel=%d gold=%d "
           "phase=%d clw=%d ccw=%d poisoned=%d\n",
        mode, player->class->name, player->lev, player->max_lev, player->au,
        borg.trait[BI_APHASE], borg.trait[BI_ACLW], borg.trait[BI_ACCW],
        player->timed[TMD_POISONED] > 0);
    return 0;
}

int teardown_tests(void *state)
{
    event_remove_handler(EVENT_MESSAGE, message, NULL);
    borg_update_entrypoint(false);
    cleanup_angband(); term_nuke(&screen); angband_term[0] = NULL; return 0;
}

static int scenario(void *state)
{
    const char *mode = getenv("SB410_MODE");
    if (!mode) mode = "pd-second";
    printf("MODE %s\n", mode);
    require(borg.goal.shop == -1 && borg.goal.ware == -1);

    /* One production useful-buy decision at the recorded state. */
    bool acted = borg_think_shop_buy_useful();
    borg_item *ware = NULL;
    int shop = -1, ware_i = -1;
    if (acted && borg.goal.shop >= 0 && borg.goal.ware >= 0) {
        shop = borg.goal.shop;
        ware_i = borg.goal.ware;
        ware = &borg_shops[shop].ware[ware_i];
    }
    printf("DECISION acted=%d shop=%d ware=%d\n", acted ? 1 : 0, shop, ware_i);
    printf("OUTCOME acted=%d shop=%d ware=%d tval=%d sval=%d\n",
        acted ? 1 : 0, shop, ware_i, ware ? ware->tval : -1,
        ware ? ware->sval : -1);
    if (ware)
        printf("CHOICE tval=%d sval=%d cost=%d desc='%s'\n",
            ware->tval, ware->sval, (int)ware->cost, ware->desc);

    if (streq(mode, "pd-second")) {
        /* Reserve pass: the cheapest affordable deficit is a phase door,
         * not the armour the valuation prefers. */
        require(acted);
        require(shop >= 0);
        require(ware != NULL);
        require(ware->tval == TV_SCROLL);
        require(ware->sval == sv_scroll_phase_door);
    } else if (streq(mode, "clw-deficit")) {
        /* Phase doors stocked: the deficit is cures, not armour. */
        require(acted);
        require(shop >= 0);
        require(ware != NULL);
        require(ware->tval == TV_POTION);
        require(ware->sval == sv_potion_cure_light
            || ware->sval == sv_potion_cure_serious
            || ware->sval == sv_potion_cure_critical);
    } else if (streq(mode, "reserve-complete")) {
        /* Reserve met: the gate is inert - the valuation resumed and acts
         * (cross-build byte identity of this mode's log is checked in the
         * evidence record; the valuation's own winner here may be any
         * stocked ware, e.g. rations). */
        require(acted);
        require(shop >= 0);
        require(ware_i >= 0);
        require(ware != NULL);
    } else if (streq(mode, "urgent-poisoned")) {
        /* Poisoned: the gate is skipped, the existing poisoned path buys
         * the cure from the alchemy shop (shop 4) on both builds. */
        require(acted);
        eq(shop, 4);
        require(ware != NULL);
        require(ware->tval == TV_POTION);
    }
    ok;
}
const char *suite_name = "native-c/startbuy-410";
struct test tests[] = {{"starting_gold_buys_the_escape_cure_reserve_first", scenario}, {NULL, NULL}};
