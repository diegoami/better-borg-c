/* Local observation/input replay. GPL-2.0-or-later or Angband licence;
 * see docs/copying.rst. Compiled only into disposable recording exports. */
#ifndef NATIVE_REPLAY_H
#define NATIVE_REPLAY_H
#include "angband.h"
#include "native-observer.h"
#include "ui-event.h"
#include "ui-term.h"
#include <time.h>
void record_init(void);
void record_finish(void);
void record_frame(const char *phase, long decisions);
bool record_input_replay(ui_event *event, bool wait, bool take, int *result);
void record_input_result(const ui_event *event, bool wait, bool take, int result);
struct keypress record_borg_key(struct keypress key);
time_t record_time(time_t *target);
const char *record_read_path(const char *path);
bool record_in_snapshot(void);
void record_snapshot_enter(void);
long measure_decision_count(void);
bool measure_snapshot_for_replay(const char *path);
#endif
