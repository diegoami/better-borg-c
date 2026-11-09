/* Product-side native C fixture for spasticscore-147, designed for the
 * 0064-corrected spastic reverse flow.  Issue:
 * diegoami/neo-angband-tracker#147.  Choreography adapted from the
 * source lane's kit (5b38022e), whose search-position walk assumed the
 * uncorrected flow and exercises nothing once patch 0064 lets the
 * reverse flow reach other grids.
 *
 * The visitation penalty in borg_flow_spastic() read ag->xtra after ag
 * had been reused by the neighbour loops, so it scored the north-west
 * neighbour's search count (for a north-wall grid, a wall grid that is
 * never searched).  The Borg stands on C=(12,2), which carries search
 * history 10 -- it has already searched where it stands -- next to
 * X=(11,2) with the same history; the fresh grids further east have
 * none.  The corner grids (1,2) and (20,2) carry history 20 so the
 * production xtra >= clevel limit takes them out of both phases.
 *
 * mismatch: with the north-west-neighbour penalty C and X look fresh
 * and C wins -- the Borg re-picks the grid it already searched.  With
 * the candidate's own count C and X drop by 400 and the fresh grid
 * (13,2) wins.
 * consistent: the north-west wall grids carry the same counts as the
 * grids they are scored for, both penalties agree everywhere, and both
 * phases pick (13,2) with identical logs. */
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
#include "mon-util.h"
#include "player.h"
#include "player-birth.h"
#include "player-calcs.h"
#include "player-util.h"
#include "ui-term.h"
#include "ui-prefs.h"
#include "borg/borg-cave.h"
#include "borg/borg-cave-util.h"
#include "borg/borg-think-dungeon-util.h"
#include "borg/borg-cave-view.h"
#include "borg/borg-flow.h"
#include "borg/borg-flow-misc.h"
#include "borg/borg-init.h"
#include "borg/borg-inventory.h"
#include "borg/borg-io.h"
#include "borg/borg-item.h"
#include "borg/borg-trait.h"
#include "borg/borg-update.h"
#include "borg/borg.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static term screen;
static int H = 22, W = 22;
/* The Borg's grid C and its searched west neighbour X on the north
 * wall. */
#define CX 12
#define XX 11
#define CY 2

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

int setup_tests(void **state)
{
    const char *profile = getenv("PS147_PROFILE");
    const char *mode    = getenv("PS147_MODE");
    if (!profile || !mode) return 1;
    set_file_paths();
    string_free(ANGBAND_DIR_USER); ANGBAND_DIR_USER = string_make(profile);
    string_free(ANGBAND_DIR_SAVE); ANGBAND_DIR_SAVE = string_make(format("%s/save", profile));
    string_free(ANGBAND_DIR_PANIC); ANGBAND_DIR_PANIC = string_make(format("%s/panic", profile));
    string_free(ANGBAND_DIR_SCORES); ANGBAND_DIR_SCORES = string_make(format("%s/scores", profile));
    string_free(ANGBAND_DIR_ARCHIVE); ANGBAND_DIR_ARCHIVE = string_make(format("%s/archive", profile));
    if (!init_angband()) { printf("SETUPFAIL init\n"); return 1; }
    create_needed_dirs();
    Rand_quick = false; Rand_state_init(147);
    if (!player_make_simple("Human", "Warrior", "Spastic147p")) { printf("SETUPFAIL birth\n"); return 1; }
    term_init(&screen, 198, 66, 256); Term_activate(&screen); angband_term[0] = &screen;
    textui_prefs_init();
    /* A closed 22x22 room, no stairs, no monsters.  Ordinary granite
     * north wall (row 1), as dungeon rooms have. */
    cave = t_build_arena(H, W);
    player->cave = cave_new(H, W);
    for (int x = 1; x < W - 1; ++x)
        square_set_feat(cave, loc(x, 1), FEAT_GRANITE);
    player_place(cave, player, loc(CX, CY));
    player->depth = player->max_depth = cave->depth = player->cave->depth = 5;
    player_exp_gain(player, player_exp[18] * player->expfact / 100);
    character_dungeon = true;
    for (int y = 1; y < H - 1; ++y) for (int x = 1; x < W - 1; ++x)
        sqinfo_on(square(cave, loc(x, y))->info, SQUARE_GLOW);
    struct object *lantern = known_item(TV_LIGHT, "Lantern", 1);
    lantern->timeout = 2000;
    inven_wield(lantern, wield_slot(lantern));
    known_item(TV_FOOD, "Ration of Food", 5);
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
    borg_alloc_detection();
    borg.c = player->grid; borg.avoidance = player->chp; borg.ready_morgoth = 0;
    /* Just arrived on the level. */
    borg.time.level = borg.time.now;
    borg.status.active = true;
    /* Fixture step: the Borg's search history.  C and its west
     * neighbour X were each searched twice (count 10); the corner
     * grids carry 20, which the production xtra >= clevel limit
     * excludes in both phases.  In the "consistent" mode the
     * north-west wall grids carry the same counts as the candidates
     * they are scored for, so both penalties agree. */
    borg_grids[CY][CX].xtra = 10;
    borg_grids[CY][XX].xtra = 10;
    borg_grids[CY][1].xtra = 20;
    borg_grids[CY][W - 2].xtra = 20;
    if (streq(mode, "consistent")) {
        borg_grids[CY - 1][CX - 1].xtra = 10;
        borg_grids[CY - 1][XX - 1].xtra = 10;
        borg_grids[CY - 1][0].xtra = 20;
        borg_grids[CY - 1][W - 3].xtra = 20;
    }
    printf("SETUP seed=147 mode=%s class=%s clevel=%d depth=%d borg=(%d,%d) "
           "C_xtra=%d X_xtra=%d corner_xtra=%d\n",
           mode, player->class->name, player->lev, player->depth, borg.c.x,
           borg.c.y, borg_grids[CY][CX].xtra, borg_grids[CY][XX].xtra,
           borg_grids[CY][1].xtra);
    return 0;
}

int teardown_tests(void *state)
{
    textui_prefs_free();
    cleanup_angband(); term_nuke(&screen); angband_term[0] = NULL; return 0;
}

/* One bored call of the production search.  The chosen grid is the one
 * the flow was enqueued for: after borg_flow_spastic() returns, it is
 * the only grid with flow cost 0. */
static int goal_x = -1, goal_y = -1;

static bool spastic_call(void)
{
    uint16_t before = messages_num();
    borg_flush();
    bool rc = borg_flow_spastic(true);
    uint16_t after = messages_num();
    goal_x = -1; goal_y = -1;
    for (int y = 0; y < H && goal_x < 0; ++y)
        for (int x = 0; x < W; ++x)
            if (borg_data_cost->data[y][x] == 0) { goal_x = x; goal_y = y; break; }
    printf("DECISION rc=%d goal=(%d,%d)\n", rc ? 1 : 0, goal_x, goal_y);
    for (int i = (int)(after - before) - 1; i >= 0; --i)
        printf("TRACK %s\n", message_str((uint16_t)i));
    return rc;
}

static int scenario_spastic(void *state)
{
    /* The production search runs once.  The chosen grid is the one the
     * flow was enqueued for (the only grid with flow cost 0).  With the
     * bug the goal is the searched grid under the Borg and the call
     * reports no step (the goal is its own grid); after the fix the
     * goal is a fresh neighbour and the call steps towards it.  The
     * verifier asserts the goal flip on these rows. */
    bool rc = spastic_call();
    /* Diagnostic: mirror the production candidate scan and print the
     * numbers (gated, not part of the assertion contract).  Run after
     * the call so borg_data_cost holds real data; its costs are the
     * goal spread, not the reverse-flow costs the scan used. */
    if (getenv("PS147_DIAG")) {
        for (int y = 1; y < H - 1; ++y) for (int x = 1; x < W - 1; ++x) {
            borg_grid *g = &borg_grids[y][x];
            if (g->feat == FEAT_NONE || g->trap || !borg_cave_floor_grid(g)) continue;
            int cost = borg_data_cost->data[y][x];
            if (cost >= 250) continue;
            if (cost >= 25 && borg.trait[BI_CLEVEL] < 30) continue;
            if (cost >= 50) continue;
            if (g->xtra >= 50) continue;
            if (g->xtra >= borg.trait[BI_CLEVEL]) continue;
            borg_grid *nb[9];
            for (int i = 0; i < 9; ++i)
                nb[i] = &borg_grids[y + ddy_ddd[i]][x + ddx_ddd[i]];
            int wall = 0, supp = 0, diag = 0, mon = 0;
            for (int i = 0; i < 4; ++i) if (nb[i]->feat >= FEAT_GRANITE) wall++;
            for (int i = 0; i < 4; ++i) {
                if (nb[i]->feat == FEAT_RUBBLE) continue;
                if (((nb[i]->feat >= FEAT_SECRET) && (nb[i]->feat <= FEAT_GRANITE))
                    || nb[i]->feat == FEAT_OPEN || nb[i]->feat == FEAT_BROKEN
                    || nb[i]->feat == FEAT_CLOSED) supp++;
            }
            for (int i = 4; i < 8; ++i) if (nb[i]->feat >= FEAT_SECRET) diag++;
            for (int i = 0; i < 8; ++i) if (nb[i]->kill) mon++;
            if (wall < 1 || diag < 2 || mon >= 1) continue;
            if (g->xtra >= borg.trait[BI_CLEVEL]) continue;
            int v_before = (supp * 500) + (diag * 100) - (nb[7]->xtra * 40)
                - (cost * 2) - borg_timer(borg.time.level)
                - (50 - borg.trait[BI_CLEVEL]) * 5;
            int v_after = (supp * 500) + (diag * 100) - (g->xtra * 40)
                - (cost * 2) - borg_timer(borg.time.level)
                - (50 - borg.trait[BI_CLEVEL]) * 5;
            printf("DIAG (%d,%d) supp=%d diag=%d own=%d nw=%d cost=%d "
                   "v_before=%d v_after=%d\n", x, y, supp, diag, g->xtra,
                   nb[7]->xtra, cost, v_before, v_after);
        }
    }
    printf("OUTCOME rc=%d goal_x=%d goal_y=%d\n", rc ? 1 : 0, goal_x, goal_y);
    require(goal_x >= 0);
    ok;
}

const char *suite_name = "native-c/spasticscore-147-product";
struct test tests[] = {
    {"spastic_search_scores_the_candidate_grid", scenario_spastic},
    {NULL, NULL}};
