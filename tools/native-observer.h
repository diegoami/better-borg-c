/* Disposable measurement observer. GPL-2.0-or-later or Angband licence;
 * see docs/copying.rst. Never compiled into the ordinary product. */
#ifndef NATIVE_OBSERVER_H
#define NATIVE_OBSERVER_H
void measure_init(void);
void measure_tick(void);
void measure_boundary(void);
void measure_decision(void);
void measure_end(void);
void measure_note(const char *text);
void measure_frame(void);
#endif
