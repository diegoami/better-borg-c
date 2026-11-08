/** Observation-only link wrappers for the immutable CBUG-0066 fixture. */
#include "angband.h"
#include "option.h"
#include "ui-menu.h"
#include "borg/borg.h"
#include "borg/borg-init.h"
#include "borg/borg-item.h"
#include "borg/borg-item-wear.h"
#include "borg/borg-trait.h"
#include "borg/borg-trait-swap.h"
#include "borg/borg-danger.h"
#include "borg/borg-io.h"
#include <stdio.h>
#include <stdlib.h>

extern bool __real_borg_backup_swap(int p);
extern int __real_borg_danger(int y, int x, int c, bool average,
    bool full_damage);
extern errr __real_borg_keypress(keycode_t key);

static bool observing;
static int entry_armour;
static int entry_weapon;
static int evaluations;
static int key_count;
static keycode_t keys[8];

static const char *boolean(bool value)
{
    return value ? "true" : "false";
}

static void critical(bool base)
{
    printf("{\"rconf\":%d,\"rblind\":%d,\"fract\":%d",
        borg.trait[BI_RCONF], borg.trait[BI_RBLIND], borg.trait[BI_FRACT]);
    if (!base) {
        printf(",\"rlite\":%d,\"rdark\":%d,\"sav\":%d",
            borg.trait[BI_RLITE], borg.trait[BI_RDARK], borg.trait[BI_SAV]);
    }
    printf("}");
}

static void candidate(int selected)
{
    const borg_item *item;
    const char *category;
    if (!selected) {
        printf("null");
        return;
    }
    item = &borg_items[selected - 1];
    category = item->tval == TV_SWORD ? "SWORD"
        : item->tval == TV_SHIELD ? "SHIELD" : "UNSUPPORTED";
    printf("{\"item\":{\"category\":\"%s\",\"quantity\":%d,"
        "\"identified\":%s,\"artifact\":%s,\"cursed\":%s,"
        "\"uncursable\":%s}}", category, item->iqty,
        boolean(item->ident), boolean(item->art_idx != 0),
        boolean(item->cursed), boolean(item->uncursable));
}

bool __wrap_borg_backup_swap(int p)
{
    bool result;
    int index = -1;
    const char *role = "none";
    int i;
    if (observing) abort();
    entry_armour = armour_swap;
    entry_weapon = weapon_swap;
    evaluations = key_count = 0;
    printf("POC {\"kind\":\"entry\",\"inputs\":{\"currentDanger\":%d,"
        "\"avoidance\":%d,\"gates\":{\"usesSwaps\":%s,\"maxDepth\":%d,"
        "\"hungry\":%s,\"weak\":%s,\"panelCount\":%d,\"nearbyUnique\":%s},"
        "\"randarts\":%s,\"baseCritical\":", p, borg.avoidance,
        boolean(borg_cfg[BORG_USES_SWAPS] != 0), borg.trait[BI_MAXDEPTH],
        boolean(borg.trait[BI_ISHUNGRY] != 0),
        boolean(borg.trait[BI_ISWEAK] != 0), borg.antibounce_count,
        boolean(borg.near.unique != 0), boolean(OPT(player, birth_randarts)));
    critical(true);
    printf(",\"candidates\":{\"armour\":"); candidate(entry_armour);
    printf(",\"weapon\":"); candidate(entry_weapon);
    printf("}},\"bindings\":{\"armourIndex\":%d,\"weaponIndex\":%d}}\n",
        entry_armour ? entry_armour - 1 : -1,
        entry_weapon ? entry_weapon - 1 : -1);
    observing = true;
    result = __real_borg_backup_swap(p);
    observing = false;
    if (result && key_count == 2 && keys[0] == 'w') {
        for (i = 0; i < z_info->pack_size; ++i) {
            if (all_letters_nohjkl[i] == keys[1]) index = i;
        }
        role = entry_armour && index == entry_armour - 1 ? "armour"
            : entry_weapon && index == entry_weapon - 1 ? "weapon"
            : "UNRECOGNIZED";
    }
    printf("POC {\"kind\":\"result\",\"swapped\":%s,\"role\":\"%s\","
        "\"nativeIndex\":%d,\"evaluationCount\":%d,\"keys\":[",
        boolean(result), role, index, evaluations);
    for (i = 0; i < key_count && i < 8; ++i) {
        printf("%s%u", i ? "," : "", (unsigned int) keys[i]);
    }
    printf("],\"keyCount\":%d}\n", key_count);
    return result;
}

int __wrap_borg_danger(int y, int x, int c, bool average, bool full_damage)
{
    /* Exactly one original evaluation; read the traits its caller guards read. */
    int value = __real_borg_danger(y, x, c, average, full_damage);
    if (observing) {
        const char *role = evaluations == 0 && entry_armour ? "armour"
            : evaluations == (entry_armour ? 1 : 0) && entry_weapon ? "weapon"
            : "UNEXPECTED";
        printf("POC {\"kind\":\"evaluation\",\"role\":\"%s\","
            "\"ordinal\":%d,\"answer\":{\"rawDanger\":%d,\"critical\":",
            role, evaluations, value);
        critical(false);
        printf("},\"nativeArmourIndex\":%d,\"nativeWeaponIndex\":%d}\n",
            armour_swap ? armour_swap - 1 : -1,
            weapon_swap ? weapon_swap - 1 : -1);
        ++evaluations;
    }
    return value;
}

errr __wrap_borg_keypress(keycode_t key)
{
    errr result = __real_borg_keypress(key);
    if (observing) {
        if (key_count < 8) keys[key_count] = key;
        ++key_count;
    }
    return result;
}
