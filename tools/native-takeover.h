/* Manual replay branching. Same licensing as native-observer.h.
 * Only added to a separate historical observer export, never to its original. */
#include <stdlib.h>

static void takeover_boundary(void)
{
    const char *requested = getenv("BORG_TAKEOVER_TURN");
    long target;
    char *end;
    FILE *receipt;
    if (!requested) return;
    errno = 0;
    target = strtol(requested, &end, 10);
    if (errno || *end || target < 1 || target > INT32_MAX)
        quit("Invalid takeover turn");
    if (turn < target) return;
    if (player->is_dead) quit("Cannot take over a dead character");
    /* record_frame just froze this command boundary in world-fingerprint.save.
     * Python verifies the complete prefix before using that native save. */
    receipt = fopen(format("%s/takeover.json", directory), "w");
    if (!receipt) quit("Cannot write takeover boundary");
    fprintf(receipt, "{\"requested_turn\":%ld,\"turn\":%ld,\"decisions\":%ld}\n",
        target, (long)turn, decisions);
    fclose(receipt);
    record_finish();
    quit(NULL);
}
