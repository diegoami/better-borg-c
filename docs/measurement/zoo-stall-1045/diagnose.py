from pathlib import Path
import json,hashlib,subprocess
b=Path('/tmp/zoo1045-diagnostic');p=b/'source/src/native-observer.c'
if (b/'build.original.json').exists(): raise ValueError('Diagnostic builds are immutable; prepare a fresh build')
s=p.read_text();s=s.replace('#include <errno.h>', '#include "player-timed.h"\n#include "cave.h"\n#include "borg/borg-cave.h"\n#include "borg/borg-flow-stairs.h"\n#include "borg/borg-flow.h"\n#include "borg/borg-item.h"\n#include "borg/borg-trait.h"\n#include <errno.h>')
old='    if (trace) fprintf(trace, "BORG %ld %s\\n", (long)turn, text);'
assert s.count(old)==1
s=s.replace(old,old+'''
    if (turn >= 59890 && (!strncmp(text, "# Fleeing level.", 16) ||
            !strncmp(text, "# Munchkin Mode.", 16))) {
        int k;
        fprintf(trace, "DETAIL turn=%ld decisions=%ld energy=%lu depth=%d pos=%d,%d borgpos=%d,%d borgdepth=%d ownfeat=%d nativefeat=%d munchkin=%d flee=%d flee_munchkin=%d less=%d goal=%d goalpos=%d,%d flow=%d packpenultimate=%d light=%d fuel=%d timeout=%d image=%d borgimage=%d up=",
            (long)turn, decisions, (unsigned long)player->total_energy,
            player->depth, player->grid.x, player->grid.y, borg.c.x, borg.c.y,
            borg.trait[BI_CDEPTH], borg_grids[borg.c.y][borg.c.x].feat,
            square(cave, player->grid)->feat, borg.munchkin_mode, borg.goal.fleeing,
            borg.goal.fleeing_munchkin, borg.goal.less, borg.goal.type,
            borg.goal.g.x, borg.goal.g.y,
            borg_data_flow->data[borg.c.y][borg.c.x], borg_items[PACK_SLOTS-2].iqty, borg.trait[BI_LIGHT], borg.trait[BI_AFUEL], borg_items[INVEN_LIGHT].timeout, player->timed[TMD_IMAGE], borg.trait[BI_ISIMAGE]);
        for (k=0;k<track_less.num;k++) fprintf(trace, "%d,%d;", track_less.x[k],track_less.y[k]);
        fprintf(trace, " down=");
        for (k=0;k<track_more.num;k++) fprintf(trace, "%d,%d;", track_more.x[k],track_more.y[k]);
        fprintf(trace, "\\n");
    }
''')
# Add one read-only print after the existing rest test, without rewriting it.
q=b/'source/src/borg/borg-think-dungeon.c';original=q.read_text()
start=original.index('static bool borg_think_dungeon_munchkin(void)')
site='    safe_place = borg_check_rest(borg.c.y, borg.c.x);'
pos=original.index(site,start)+len(site)
note='\n    if (borg.time.now >= 12300) borg_note(format("DIAG safe=%d scary=%d hp=%d/%d hungry=%d weak=%d", safe_place, borg.mon.scary, borg.trait[BI_CURHP], borg.trait[BI_MAXHP], borg.trait[BI_ISHUNGRY], borg.trait[BI_ISWEAK]));'
q.write_text(original[:pos]+note+original[pos:])
assert q.read_text().replace(note,'',1)==original
(b/'dungeon.original.sha256').write_text(hashlib.sha256(original.encode()).hexdigest()+'\n')
(b/'build.original.json').write_bytes((b/'build.json').read_bytes());p.write_text(s)
with (b/'diagnostic-build.log').open('w') as f: subprocess.run(['cmake','--build',str(b/'build'),'--target','OurExecutable','--parallel','2'],stdout=f,stderr=subprocess.STDOUT,check=True)
d=json.loads((b/'build.json').read_text());d['diagnostic']='Additive known-state prints in measure_note; existing decision expressions unchanged; one additive read-only decision note; verbosity configured separately';d['observer_diagnostic_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();d['binary_sha256']=hashlib.sha256((b/'build/game/angband').read_bytes()).hexdigest();(b/'build.json').write_text(json.dumps(d,indent=2)+'\n')
