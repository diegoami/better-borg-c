/* Product-side native C fixture for the necrolight-296 crash correction.
 * Source proposal: diegoami/neo-angband-tracker#296, carried as patch
 * 0099; this fixture covers the correction of the crash that patch
 * introduced (reported by the borg-rs lane, borg-rs#21).
 *
 * Patch 0099 made the Necromancer spell-failure estimate add the game's
 * lit-square penalty by testing square_islit(cave, borg.c).  The Borg's
 * recorded position (borg.c) is refreshed by the map update, so on the
 * first think after changing levels it still holds the previous
 * level's position.  square_islit() bounds-asserts its argument, but
 * the product compiles the asserts out, so on a smaller new level the
 * stale position reads outside the new chunk's square array
 * (square_light() -> square(c, grid)->light).  borg-rs reproduced a
 * SIGSEGV in every Necromancer game at the first return to town
 * (dungeon 176x57 -> town 66x22, stale borg.c = (117,47)).
 *
 * Modes:
 *   stale-far  - the fail-before anchor.  The same missing bounds
 *                check, exercised with an out-of-bounds position far
 *                enough outside a small cave that the unguarded read
 *                hits unmapped memory deterministically instead of
 *                layout-dependent heap garbage.  Before the correction
 *                this mode dies with SIGSEGV; after it, the stale
 *                position is treated as unlit and the estimate equals
 *                the dark baseline.
 *   stale-town - the recorded town geometry (66x22 cave, stale
 *                (117,47)).  The unguarded read here is
 *                layout-dependent, so this mode is documented
 *                context, not the fail-before anchor.
 *   lit, dark  - in-bounds negative controls locking patch 0099's
 *                behaviour: the lit square adds the penalty, the dark
 *                square does not.
 *   mage-lit   - class-check control: a non-Necromancer caster on the
 *                same lit square takes no penalty.
 */
#include "unit-test.h"
#include "test-utils.h"
#include "cave.h"
#include "game-world.h"
#include "init.h"
#include "message.h"
#include "object.h"
#include "obj-gear.h"
#include "obj-knowledge.h"
#include "obj-make.h"
#include "obj-pile.h"
#include "obj-util.h"
#include "player.h"
#include "player-birth.h"
#include "player-calcs.h"
#include "player-util.h"
#include "ui-term.h"
#include "ui-prefs.h"
#include "borg/borg-cave.h"
#include "borg/borg-cave-view.h"
#include "borg/borg-init.h"
#include "borg/borg-inventory.h"
#include "borg/borg-magic.h"
#include "borg/borg-trait.h"
#include "borg/borg-update.h"
#include "borg/borg.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static term screen;
static int H = 22, W = 22;
/* Dark reference grid inside the cave, beyond torch radius. */
#define DX 16
#define DY 11
/* Recorded stale position from the borg-rs town reproduction. */
#define STALE_TOWN loc(117, 47)
/* The deterministic fail-before anchor position. */
#define STALE_FAR loc(20000, 20000)

static struct object *known_item(int tval, const char *name, int number)
{
    struct object *obj       = object_new();
    struct object_kind *kind = lookup_kind(tval, lookup_sval(tval, name));
    if (!kind) { fprintf(stderr, "MISSING KIND %s\n", name); quit("fixture item kind missing"); }
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

/* The borg_magic record matching a spell enum. */
static borg_magic *magic_of(enum borg_spells spell)
{
    if (!borg_magics) return NULL;
    for (int i = 0; i < player->class->magic.total_spells; ++i)
        if (borg_magics[i].spell_enum == spell) return &borg_magics[i];
    return NULL;
}

int setup_tests(void **state)
{
    const char *profile = getenv("NL296_PROFILE");
    const char *mode    = getenv("NL296_MODE");
    if (!profile || !mode) return 1;
    bool mage = streq(mode, "mage-lit");
    bool dark = streq(mode, "dark");
    set_file_paths();
    string_free(ANGBAND_DIR_USER); ANGBAND_DIR_USER = string_make(profile);
    string_free(ANGBAND_DIR_SAVE); ANGBAND_DIR_SAVE = string_make(format("%s/save", profile));
    string_free(ANGBAND_DIR_PANIC); ANGBAND_DIR_PANIC = string_make(format("%s/panic", profile));
    string_free(ANGBAND_DIR_SCORES); ANGBAND_DIR_SCORES = string_make(format("%s/scores", profile));
    string_free(ANGBAND_DIR_ARCHIVE); ANGBAND_DIR_ARCHIVE = string_make(format("%s/archive", profile));
    if (!init_angband()) { printf("SETUPFAIL init\n"); return 1; }
    create_needed_dirs();
    Rand_quick = false; Rand_state_init(296);
    if (!player_make_simple("Human", mage ? "Mage" : "Necromancer", "NecroCrash296")) {
        printf("SETUPFAIL birth\n"); return 1;
    }
    term_init(&screen, 198, 66, 256); Term_activate(&screen); angband_term[0] = &screen;
    if (streq(mode, "stale-town")) { H = 22; W = 66; }
    /* A closed cave, floor everywhere.  The player's 3x3 patch is
     * permanently lit (town-like) in every mode but dark, which stays
     * unlit and unequipped so the player's own square reads dark. */
    cave = t_build_arena(H, W);
    player->cave = cave_new(H, W);
    player_place(cave, player, loc(11, 11));
    player->depth = player->max_depth = cave->depth = player->cave->depth = 5;
    player_exp_gain(player, player_exp[18] * player->expfact / 100);
    character_dungeon = true;
    if (!dark) {
        for (int y = 10; y <= 12; ++y) for (int x = 10; x <= 12; ++x)
            sqinfo_on(square(cave, loc(x, y))->info, SQUARE_GLOW);
        struct object *torch = known_item(TV_LIGHT, "Wooden Torch", 1);
        torch->timeout = 2000;
        inven_wield(torch, wield_slot(torch));
    }
    player->upkeep->update |= PU_BONUS | PU_HP | PU_TORCH | PU_INVEN;
    update_stuff(player);
    player->chp = player->mhp;
    borg_rand_local = 1000; borg_init();
    if (borg_init_failure || borg_cfg[BORG_CHEAT_DEATH] || OPT(player, cheat_live)) { printf("SETUPFAIL borg\n"); return 1; }
    borg_equipment(); borg_inventory(); borg_notice(true);
    for (int y = 0; y < H; ++y) for (int x = 0; x < W; ++x) {
        borg_grids[y][x].feat = square(cave, loc(x, y))->feat;
        borg_grids[y][x].info |= BORG_OKAY | BORG_VIEW;
    }
    borg.c = player->grid; borg.avoidance = player->chp; borg.ready_morgoth = 0;
    /* Just arrived on the level - the map update has not run yet, and
     * the stale modes keep it that way by setting borg.c directly. */
    borg.time.level = borg.time.now;
    borg.status.active = true;
    borg_cheat_spells();
    update_view(cave, player);
    enum borg_spells spell = mage ? MAGIC_MISSILE : NETHER_BOLT;
    borg_magic *as = magic_of(spell);
    if (!as) { printf("SETUPFAIL spell_enum\n"); return 1; }
    /* Level-neutral estimate: failure base = as->sfail, no stat or
     * level adjustment, no fear or stun. */
    borg.trait[BI_CLEVEL] = as->level;
    borg.trait[BI_FAIL1] = 0;
    borg.trait[BI_FAIL2] = 0;
    printf("SETUP seed=296 mode=%s class=%s spell_num_sfails=%d level=%d "
           "lit_own=%d lit_dark=%d\n", mode, player->class->name,
           as->sfail, as->level,
           square_islit(cave, player->grid) ? 1 : 0,
           square_islit(cave, loc(DX, DY)) ? 1 : 0);
    return 0;
}

int teardown_tests(void *state)
{
    textui_prefs_free();
    cleanup_angband(); term_nuke(&screen); angband_term[0] = NULL; return 0;
}

/* One production estimate per position.  Nether Bolt is the
 * Necromancer's level-1 spell: a low failure base, so the +25 lit
 * penalty stays visible under the 50% cap (Vampire Strike's base is
 * already 50). */
static int fail_at(struct loc grid) { borg.c = grid; return borg_spell_fail_rate(NETHER_BOLT); }
static int fail_mage_at(struct loc grid) { borg.c = grid; return borg_spell_fail_rate(MAGIC_MISSILE); }

static int scenario_necro_crash(void *state)
{
    const char *mode = getenv("NL296_MODE");
    if (!mode) mode = "lit";
    bool dark = streq(mode, "dark");
    bool lit  = streq(mode, "lit");
    bool town = streq(mode, "stale-town");
    bool far  = streq(mode, "stale-far");
    bool mage = streq(mode, "mage-lit");
    printf("MODE %s\n", mode);

    if (mage) {
        /* Class check: the same lit own square must leave the Mage's
         * estimate untouched. */
        int litc = fail_mage_at(player->grid);
        int darkc = fail_mage_at(loc(DX, DY));
        printf("OUTCOME lit=%d dark=%d delta=%d\n", litc, darkc, litc - darkc);
        require(square_islit(cave, player->grid));
        require(!square_islit(cave, loc(DX, DY)));
        require(darkc >= 5 && darkc <= 50);
        require(litc == darkc);
        borg.c = player->grid;
        ok;
    }

    if (dark) {
        /* In-bounds dark square: no penalty (0099's dark behaviour). */
        int darkc = fail_at(player->grid);
        printf("OUTCOME dark=%d\n", darkc);
        require(!square_islit(cave, player->grid));
        require(darkc >= 5 && darkc <= 50);
        ok;
    }

    /* Necromancer modes: reference the lit own square and the dark
     * grid, then (stale modes) the out-of-bounds position. */
    int litc = fail_at(player->grid);
    int darkc = fail_at(loc(DX, DY));
    int expect_lit = darkc + 25;
    if (expect_lit > 50) expect_lit = 50;
    if (expect_lit < 5) expect_lit = 5;
    printf("OUTCOME lit=%d dark=%d delta=%d", litc, darkc, litc - darkc);
    if (town || far) {
        int stalec = fail_at(town ? STALE_TOWN : STALE_FAR);
        printf(" stale=%d\n", stalec);
        /* The stale position is out of bounds; the guarded estimate
         * treats it as unlit and returns the dark baseline.  Before
         * the correction this call read outside the square array
         * (stale-far deterministically unmapped: SIGSEGV). */
        require(stalec == darkc);
    } else {
        printf("\n");
        /* In-bounds lit square: the 0099 penalty applies. */
        require(square_islit(cave, player->grid));
        require(!square_islit(cave, loc(DX, DY)));
        require(litc == expect_lit);
        require(darkc >= 5 && darkc <= 50);
    }
    require(litc >= 5 && litc <= 50);
    borg.c = player->grid;
    ok;
}

const char *suite_name = "native-c/necrolight-296-crash";
struct test tests[] = {
    {"necrolight_stale_position_bounds_guard", scenario_necro_crash},
    {NULL, NULL}
};
