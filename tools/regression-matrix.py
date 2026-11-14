#!/usr/bin/env python3
"""Rerun the accumulated prior-fixture regression matrix against a product build.

Every earlier native carry's fixture is linked against the given build's
core objects and executed, and each case is checked against its recorded
expectation:

* local-baseline groups (all 60 local fixtures, committed under
  docs/audit/c-reports/) are also compared value-for-value against the
  OUTCOME rows of their recorded baseline logs, and byte-identity to those
  baselines is reported per case.
  A byte difference is information, not a failure: later carries
  legitimately touch shared paths.  A row difference is a failure unless
  the mode declares an intentional transition.
* source-tracker kit groups (the milestone-6/0064-0067 kits whose
  worktrees are retired; the fixtures are fetched at the ledger's
  evidence pins through the kit's own run-cases.py) must pass every mode,
  and the rows recorded here become their baseline for future reruns.
  recallmana-157 is the declared standing exception: the unchanged kit
  fixture stays red on the product since the 0053 flee branch (asserted
  by tools/verify-recallmana.py; the fail-before/pass-after proof used an
  adapted one-line fixture, see RECALL-MANA.md and the milestone 6
  layered-interaction section).

Declared intentional transitions (from the original 0049-era run, kept
asserted): dispel-248 'undead' must keep the losdispel-326 replaced
launch values and the undead refusal outcome; dispel-259 'reserve' and
'clear' must keep failing (the blast scan the losdispel correction made
reachable moves their absolute values).  Added at milestone 9: dispel-248
'living' fails its rating contract and vampire-257 'near-far'/'near-near'
record the refusal instead of the cast — necrolight-296 (0099) makes the
Necromancer's failure estimate match the game on lit squares, so the borg
declines spells it previously cast on the undershot estimate; attributed
by rerunning both groups at every carry build 0091-0098 and the 0099
build, with the new rows pinned by rows_must.

Usage (under the shared validation lock):
  python3 tools/regression-matrix.py --build build/native --output artifacts/m7-matrix
Every local group's fixture is committed under docs/audit/c-reports/, so
the local matrix needs nothing outside the clone.  The KIT_GROUPS fetch
their fixtures at the ledger's evidence commits, so they need those commits
present (a full clone, not a shallow one).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# name, baseline dir (repo-root relative), env tag, modes, options.
# Options: scenario= overrides the fixture source; no_profile omits the
# TAG_PROFILE variable (the fixture does not read it); env= adds fixed
# environment; fail= modes expected not to pass (with reason);
# rows_free= modes exempt from the baseline-row comparison;
# rows_must= extra required OUTCOME pairs for a mode;
# baseline_log= callable giving the baseline log name for a mode.
GROUPS = [
    # --- the 0049-era matrix (carries 1-48) ---
    ('swap', 'docs/audit/c-reports/swap', 'CBUG0066',
     ('armour-better', 'weapon-better', 'armour-only', 'weapon-only', 'tie',
      'no-benefit', 'both-helpful', 'electric-weapon', 'fire-armour'), {}),
    ('knockout', 'docs/audit/c-reports/knockout', 'CBUG0002',
     ('knockout', 'heavy-stun', 'paralysis', 'none'),
     {'cflags': ['-Dborg_dont_react=borg.dont_react'],
      'rows_free': ('paralysis',),
      'rows_must': {'paralysis': {'delta': 3}},
      'rows_note': 'paralysis: painmsg-197 (0071) shifts the absolute reaction '
                   'counts by +1 (reactions_before 0 -> 1, after 3 -> 4) while '
                   'the knockout fix invariant delta=3 is preserved — attributed '
                   'by rerunning the mode at the 0070-after build (0/3) and the '
                   '0071-applied build (1/4)'}),
    ('preparation', 'docs/audit/c-reports/preparation', 'CBUG0094',
     ('regen-only', 'speed-wins', 'speed-only', 'already-active', 'unlearned',
      'low-mana', 'town', 'blind', 'confused'), {}),
    ('cold-protection', 'docs/audit/c-reports/cold-protection', 'CBUG0004',
     ('acid-only', 'cold-only', 'neither', 'both', 'physical-acid-control',
      'physical-cold-control'), {}),
    ('rings', 'docs/audit/c-reports/rings', 'CBUG0062',
     ('left-ready', 'right-charging-left-ready', 'right-control', 'both-ready',
      'no-ring', 'left-charging', 'blind-control'), {}),
    ('potion-timing', 'docs/audit/c-reports/potion-timing', 'CBUG0061',
     ('long-gap', 'recent', 'boundary-four', 'same-turn', 'bypass-control',
      'first-use', 'first-turn', 'empty-control', 'reserve-control'), {}),
    ('itangast', 'docs/audit/c-reports/itangast', 'CBUG0086',
     ('named-dragon', 'ogre-control', 'unseen-control', 'it-control',
      'lower-it-control'), {}),
    ('shot-path', 'docs/audit/c-reports/shot-path', 'SHOTPATH279',
     ('clear-path', 'blocked', 'ball-control', 'direct-control',
      'boulder-control', 'boulder-blocked'), {}),
    ('per-spell', 'docs/audit/c-reports/per-spell', 'CBUG0048',
     ('clear-path', 'blocked', 'ball-control', 'direct-control',
      'boulder-control'),
     {'baseline_log': lambda mode: f'both-after-{mode}.log'}),
    ('glyph', 'docs/audit/c-reports/glyph', 'CBUG0102',
     ('stairs', 'clear-floor', 'pairing'), {}),
    ('missile', 'docs/audit/c-reports/missile', 'M254',
     ('no-target', 'live-shot', 'simulated'), {}),
    ('tp-other', 'docs/audit/c-reports/tp-other', 'CBUG0051',
     ('two-phase', 'no-morgoth-phase', 'single'), {}),
    ('dispel', 'docs/audit/c-reports/dispel', 'D248',
     ('living', 'undead', 'bolt'),
     {'scenario': 'tools/dispel-filter-scenario.c',
      'rows_free': ('undead',),
      'fail': ('living',),
      'fail_reason': 'necrolight-296 (0099): on a lit square the '
                     "Necromancer's spell-failure estimate now matches the "
                     'game (+25 on any lit square, square_islit), crosses '
                     "the borg's 25% limit and the spell gate closes "
                     '(GATE spell_okay=0, RATING value=0 where the fixture '
                     'expects the rated value dam + reward - mana cost); '
                     "the scenario's own game-level cast still applies the "
                     'damage, so the OUTCOME rows are unchanged — only the '
                     'rating contract, written for the pre-fix estimate, '
                     'fails.  Attributed by rerunning the group at every '
                     'carry build 0091-0098 (self-check green, old rows) '
                     'and the 0099 build (this transition).',
      'rows_must': {'living': {'hp_before': 225, 'hp_after': 159, 'hp_lost': 66,
                               'undead': 0},
                    'undead': {'hp_before': 47, 'hp_after': 47, 'hp_lost': 0,
                               'undead': 1}}}),
    ('arc', 'docs/audit/c-reports/arc', 'A253',
     ('arc-bystander', 'arc-both'), {}),
    ('munchkin', 'docs/audit/c-reports/munchkin', 'M244',
     ('phantom', 'on-stair'), {}),
    ('vampire', 'docs/audit/c-reports/vampire', 'V257',
     ('near-far', 'near-near', 'far'),
     {'fail': ('near-far', 'near-near'),
      'fail_reason': 'necrolight-296 (0099): the scenario Necromancer '
                     'stands in a lit square, so the fix makes the Vampire '
                     'Strike failure estimate match the game (33% vs the '
                     "old 8%); the borg refuses the spell over its 25% "
                     'limit and takes no action (acted=0 keys=0 '
                     'cast_spell=0 — exactly the kit lit-mode after-row) '
                     'where the pre-fix borg cast on the undershot '
                     'estimate.  Attributed by rerunning the group at every '
                     'carry build 0091-0098 (cast rows, self-check green) '
                     'and the 0099 build (refusal rows); the far control '
                     'keeps its out-of-range refusal in both.',
      'rows_free': ('near-far', 'near-near'),
      'rows_must': {'near-far': {'acted': 0, 'keys': 0, 'cast_spell': 0},
                    'near-near': {'acted': 0, 'keys': 0, 'cast_spell': 0}}}),
    ('slay', 'docs/audit/c-reports/slay', 'S239',
     ('animal', 'nonanimal'), {}),
    ('detect', 'docs/audit/c-reports/detect', 'D290',
     ('stale', 'fresh'), {}),
    ('activ', 'docs/audit/c-reports/activ', 'A260',
     ('miswired', 'control'), {}),
    ('reserve', 'docs/audit/c-reports/reserve', 'R258',
     ('veto', 'control'), {}),
    ('dispel259', 'docs/audit/c-reports/dispel259', 'D259',
     ('reserve', 'clear'),
     {'fail': ('reserve', 'clear'),
      'fail_reason': 'losdispel-326 makes the radius-10 blast scan reachable; '
                     'the absolute eq moves (recorded +296 at the 0049 tip)',
      'rows_free': ('reserve', 'clear')}),
    ('losdispel', 'docs/audit/c-reports/losdispel', 'L326',
     ('storm', 'control'), {}),
    ('staff', 'docs/audit/c-reports/staff', 'S262',
     ('holy', 'control'), {}),
    ('blind', 'docs/audit/c-reports/blind', 'B261',
     ('blind', 'control'), {}),
    ('text', 'docs/audit/c-reports/text', 'T287',
     ('multibyte', 'control'),
     {'skip': 'retired: targets the pre-0068 five-argument borg_what_text '
              'signature and no longer compiles against the tip; superseded '
              'by the text-bufsize kit (0068) in this matrix'}),
    ('calcreload', 'docs/audit/c-reports/calcreload', 'T325',
     ('reload', 'control'), {'no_profile': True}),
    ('staletarget', 'docs/audit/c-reports/staletarget', 'T322',
     ('stale', 'control'), {}),
    ('glowoverflow', 'docs/audit/c-reports/glowoverflow', 'T311',
     ('glow', 'control'), {}),
    ('light', 'docs/audit/c-reports/light', 'T238',
     ('phial', 'torch'), {}),
    ('surrounded', 'docs/audit/c-reports/surrounded', 'T312',
     ('traps', 'walls'), {}),
    ('homeblows', 'docs/audit/c-reports/homeblows', 'T313',
     ('stack', 'single'), {}),
    ('lunal', 'docs/audit/c-reports/lunal', 'T314',
     ('town', 'pack'), {}),
    ('opblock', 'docs/audit/c-reports/opblock', 'T324',
     ('operators', 'control'), {'no_profile': True}),
    ('calfree', 'docs/audit/c-reports/calfree', 'T323',
     ('free', 'control'), {'no_profile': True}),
    ('brand', 'docs/audit/c-reports/brand', 'N240', ('brand', 'control'), {}),
    ('stairtrack', 'docs/audit/c-reports/stairtrack', 'T232', ('known', 'fresh'), {}),
    ('acidarc', 'docs/audit/c-reports/acidarc', 'AC252', ('edge', 'near', 'empty'), {}),
    ('outoflight', 'docs/audit/c-reports/outoflight', 'OL229',
     ('dying', 'lit', 'everburn', 'dead'), {}),
    ('mapwall', 'docs/audit/c-reports/mapwall', 'MW212',
     ('door-close', 'door-open', 'no-change'), {}),
    ('enlightenment', 'docs/audit/c-reports/enlightenment', 'CBUG0065',
     ('dungeon', 'town-control', 'unknown-control', 'unrelated-control',
      'augmentation-dungeon', 'augmentation-town'), {}),
    ('stairreturn', 'docs/audit/c-reports/stairreturn', 'SR230',
     ('stairs-dead-torch', 'lit', 'dead-no-stairs'), {}),
    ('blowname', 'docs/audit/c-reports/blowname', 'BW247', ('plain',),
     {'env': {'ASAN_OPTIONS': 'halt_on_error=0:detect_leaks=0'},
      'baseline_log': lambda mode: 'normal-after.log'}),
    ('excavate', 'docs/audit/c-reports/excavate', 'EV236', ('excavate', 'no-target'), {}),
    ('calllight', 'docs/audit/c-reports/calllight', 'CL231', ('own-open-door', 'floor'), {}),
    ('gloves', 'docs/audit/c-reports/gloves', 'GL205',
     ('glove-fa', 'plain', 'have-fa'), {}),
    ('detectcarry', 'docs/audit/c-reports/detectcarry', 'DC219',
     ('new-level', 'same-level'), {}),
    ('maimfoe', 'docs/audit/c-reports/maimfoe', 'MF256',
     ('wrong-return', 'single', 'none'), {}),
    ('recalldepth', 'docs/audit/c-reports/recalldepth', 'RD310',
     ('endgame', 'generic', 'mismatch'), {}),
    # --- kits retained under .worktrees/ since 0050 ---
    ('glowtrace-213', 'docs/audit/c-reports/glowtrace-213', 'GLOW213',
     ('main',), {'no_mode_env': True,
                 'baseline_log': lambda mode: 'normal-after-main.log'}),
    ('glow-isglow', 'docs/audit/c-reports/glow-isglow', 'GLOW213',
     ('main', 'door', 'torchlit', 'unlit'), {}),
    ('text-bufsize', 'docs/audit/c-reports/text-bufsize', 'T287',
     ('multibyte', 'control', 'wide'), {}),
    ('iswarded-198', 'docs/audit/c-reports/iswarded-198', 'ISW198',
     ('rune-town', 'hit-town', 'rune-inside', 'hit-inside', 'hit-noglyph'), {}),
    ('painmsg-197', 'docs/audit/c-reports/painmsg-197', 'PM197',
     ('held', 'command', 'uncommand', 'shapefail', 'stun', 'hurt', 'puff'),
     {'fail': ('puff',),
      'fail_reason': 'outside the fix: the puff line has no monster name and '
                     'stays unrecognised in both phases (kit contract)'}),
    ('trollswap-201', 'docs/audit/c-reports/trollswap-201', 'TS201',
     ('troll-orc', 'troll-plain'), {}),
    ('drophole-136', 'docs/audit/c-reports/drophole-136', 'DH136',
     ('salt-water', 'spare-esp', 'restore-mana', 'level30'), {}),
    ('wearskip-85', 'docs/audit/c-reports/wearskip-85', 'WS85',
     ('tight', 'roomy', 'nocloak'), {}),
    ('lantern-90', 'docs/audit/c-reports/lantern-90', 'LN90',
     ('empty', 'single'), {}),
    ('homebanish-54', 'docs/audit/c-reports/homebanish-54', 'HB54',
     ('banish', 'mass'), {}),
    ('necrolight-crash', 'docs/audit/c-reports/necrolight-296-crash', 'NL296',
     ('stale-town', 'stale-far', 'lit', 'dark', 'mage-lit'), {}),
    # Source63 (issue 63, CBUG-0047): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-hitchance63.py.
    ('hitchance-63', 'docs/audit/c-reports/hitchance-63', 'HC63',
     ('brute', 'wretch'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),
    # Source98 (issue 98, CBUG-0082): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-flowkillhall98.py.
    ('flowkillhall-98', 'docs/audit/c-reports/flowkillhall-98', 'FK98',
     ('hall', 'hallctl', 'leak', 'reverse'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),
    # Source73 (issue 73, CBUG-0057): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-lunaltake73.py.
    ('lunaltake-73', 'docs/audit/c-reports/lunaltake-73', 'LT73',
     ('dagger', 'dagger-munchkin', 'gold'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),
    # Source34 (issue 34, CBUG-0016): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-stairphase34.py.
    ('stairphase-34', 'docs/audit/c-reports/stairphase-34', 'SP34',
     ('upstair', 'antisummon', 'downstair', 'floor', 'climb'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source71 (issue 71, CBUG-0055): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-takestair71.py.
    ('takestair-71', 'docs/audit/c-reports/takestair-71', 'TS71',
     ('take', 'scum', 'lunal', 'control'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source108 (issue 108, CBUG-0092): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-restprep108.py.
    ('restprep-108', 'docs/audit/c-reports/restprep-108', 'RP108',
     ('pfe', 'clevel30'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source234 (issue 234): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-prepreason234.py.
    ('prepreason-234', 'docs/audit/c-reports/prepreason-234', 'PR234',
     ('nodeeper100', 'default127', 'prepared97'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source61 (issue 61, CBUG-0045): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-losecon61.py.
    ('losecon-61', 'docs/audit/c-reports/losecon-61', 'LC61',
     ('lowcon', 'lowstr', 'neither', 'bothlow'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source66 (issue 66, CBUG-0050): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-crushv266.py.
    ('crushv2-66', 'docs/audit/c-reports/crushv2-66', 'CR66',
     ('caster', 'archer', 'melee', 'tough'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source68 (issue 68, CBUG-0052): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-granitesim68.py.
    ('granitesim-68', 'docs/audit/c-reports/granitesim-68', 'G68',
     ('rubble', 'floor', 'granite'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source100 (issue 100, CBUG-0084): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-scootidx100.py.
    ('scootidx-100', 'docs/audit/c-reports/scootidx-100', 'SC100',
     ('north', 'south', 'pack'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source60 (issue 60, CBUG-0044): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-emptyslot60.py.
    ('emptyslot-60', 'docs/audit/c-reports/emptyslot-60', 'ES60',
     ('empty', 'oil'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source80 (issue 80, CBUG-0064): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-eathurt80.py.
    ('eathurt-80', 'docs/audit/c-reports/eathurt-80', 'EH80',
     ('fullhp', 'hurt'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source86 (issue 86, CBUG-0070): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-ringslot86.py.
    ('ringslot-86', 'docs/audit/c-reports/ringslot-86', 'RS86',
     ('swap', 'mirror', 'empty'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source31 (issue 31, CBUG-0012): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-swaptrial31.py.
    ('swaptrial-31', 'docs/audit/c-reports/swaptrial-31', 'ST31',
     ('swap-held', 'no-weapon-swap', 'no-candidate'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source29 (issue 29, CBUG-0010): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-homeskip29.py.
    ('homeskip-29', 'docs/audit/c-reports/homeskip-29', 'HS29',
     ('stored-first', 'stored-last', 'no-history'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source132 (issue 132, CBUG-0116): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-sellcharges132.py.
    ('sellcharges-132', 'docs/audit/c-reports/sellcharges-132', 'SC132',
     ('stack', 'stack-emptyhome', 'single', 'none'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Source133 (issue 133, CBUG-0117): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-egosell133.py.
    ('egosell-133', 'docs/audit/c-reports/egosell-133', 'ES133',
     ('plain-worn', 'aman-worn'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),
    # Source95 (issue 95, CBUG-0079): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-newkill95.py.
    ('newkill-95', 'docs/audit/c-reports/newkill-95', 'T95',
     ('wall', 'floor'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),
    # Source116 (issue 116, glyphtrack): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-glyph116.py.
    ('glyphtrack-116', 'docs/audit/c-reports/glyphtrack-116', 'GT116',
     ('complete-sea', 'new-sea'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),
    # Source193 (issue 193, lunaltele): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-lunaltele193.py.
    ('lunaltele-193', 'docs/audit/c-reports/lunaltele-193', 'LT193',
     ('teleto', 'teleaway', 'teleaway-unseen', 'shriek', 'teleto-nolunal'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),
    # Source101 (issue 101, deaduniq): after-baselines from the product run; the
    # before phase is the documented flip in tools/verify-deaduniq101.py.
    ('deaduniq-101', 'docs/audit/c-reports/deaduniq-101', 'DU101',
     ('wear', 'junk', 'junk-nokitpotion', 'alive-wear', 'alive-junk', 'wear-noscrolls'),
     {'baseline_log': lambda mode: f'after-{mode}.log'}),

    # Improvement I-002 (issue408, fleeing-heal): the baseline logs are the
    # before-build (ac0cc65c5) runs.  There the flee-low case replays the
    # recorded D0017 fatal decision - fleeing, poisoned, 7 HP, safe grid,
    # cures in pack - and rests for recall over the poison (heal=0 rest=1,
    # the fixture fails its after-contract 0/1).  The merged product queues
    # the Herbal Curing cure instead, so flee-low rows legitimately change
    # and rows_must pins the after-contract.  The three controls (recall
    # buy-time quaff at real danger, the existing not-fleeing heal path,
    # and the healthy recall rest) were byte-identical across the
    # before/after builds and must stay that way.
    ('fleeheal-408', 'docs/audit/c-reports/fleeheal-408', 'IM2',
     ('flee-low', 'flee-highdanger', 'noflee-wounded', 'flee-full'),
     {'scenario': 'tools/fleeing-heal-scenario.c',
      'rows_free': ('flee-low',),
      'rows_must': {'flee-low': {'acted': 1, 'heal': 1, 'rest': 0, 'keys': 3},
                    'flee-highdanger': {'acted': 1, 'heal': 1, 'rest': 0, 'keys': 2},
                    'noflee-wounded': {'acted': 1, 'heal': 1, 'rest': 0, 'keys': 3},
                    'flee-full': {'acted': 1, 'heal': 0, 'rest': 1, 'keys': 5}}}),
]

# Source-tracker kit groups (retired worktrees; fixtures at the ledger's
# evidence pins). name, evidence ref, declared expectations.
KIT_GROUPS = [
    ('stairrange-245', '3c9a75e20233', {}),
    ('clockreset-246', '85ff225404d9', {}),
    ('dangerflee-156', '809e556b39e4', {}),
    ('recallmana-157', 'b6bd252e1c9b',
     {'fail': ('lowmana',),
      'fail_reason': 'standing 0053 interaction: an ordinary Borg in excessive '
                     'danger flees via desperate stairs before the recall-wait '
                     'line, so the unchanged lowmana fixture stays red '
                     '(verify-recallmana asserts exactly this: lowmana red, '
                     'halfmana green, restore_mana=0 in both)',
      'rows_must': {'lowmana': {'restore_mana': 0}, 'halfmana': {'restore_mana': 0}}}),
    ('deskstair-153', '366fd1b08c4d', {}),
    ('backaway-155', 'fa0293e587d8', {}),
    ('cfghang-141', 'a3164a61b830', {}),
    ('cfgminus-142', '18f79a3cc631', {}),
    ('cfgmissing-144', '1ff9ca1e59d6', {}),
    ('countsell-134', '68b23b2a1b2e', {}),
    ('drainedive-235', '557c85260f8b', {}),
    ('respois-184', 'af01d73ccfcb', {}),
    ('respoiswar-185', '6f130a4eea68', {}),
    ('spastic-146', 'da9a39f4da30', {}),
    ('glyphflow-345', 'fbe06401c54c', {}),
    ('swapacid-199', '9eca003a5896', {}),
    ('staircycle-403', '43dee40ed052', {}),
]

TAG_RE = re.compile(r"(\w+)'?\s*\+\s*'?_PROFILE|(\w+)_PROFILE")


def git_show(ref, path):
    return subprocess.check_output(['git', 'show', ref + ':' + path], cwd=ROOT)


def git_ls(ref, path):
    out = subprocess.check_output(['git', 'ls-tree', '--name-only', ref, path],
                                  cwd=ROOT, text=True)
    return [line.rstrip('/') for line in out.splitlines() if line.strip()]


def baseline_rows(text):
    m = re.search(r'OUTCOME (.*)', text)
    if not m:
        return None
    return {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', m.group(1))}


def baseline_log_name(dirpath, mode, opts):
    fn = opts.get('baseline_log')
    if fn:
        return fn(mode)
    for name in (f'{mode}.log', f'normal-after-{mode}.log', f'after-{mode}.log'):
        if (dirpath / name).exists():
            return name
    return None


def run_group(name, tag, modes, dest, objects, opts, build):
    # cflags: compile-time compat for an unchanged fixture. The knockout
    # fixture reads the removed borg_dont_react global; official master keeps
    # the same state in borg.dont_react.
    link = ['cc', '-g', '-DALLOW_BORG', *opts.get('cflags', []), '-I' + str(ROOT / 'src'),
            '-I' + str(ROOT / 'src/tests'), str(dest / 'scenario.c'),
            *map(str, objects), '-lm', '-o', str(dest / 'scenario')]
    with (dest / 'link.log').open('w') as log:
        subprocess.run(link, stdout=log, stderr=subprocess.STDOUT, check=True)
    cases = {}
    for mode in modes:
        env = {'LC_ALL': 'C.UTF-8'}
        if not opts.get('no_mode_env'):
            env[tag + '_MODE'] = mode
        if not opts.get('no_profile'):
            env[tag + '_PROFILE'] = str(dest / 'profile')
        env.update(opts.get('env', {}))
        result = subprocess.run(
            [str(dest / 'scenario'), '-v'], cwd=build / 'game', env=dict(os.environ, **env),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
        (dest / (mode + '.log')).write_text(text)
        passed = ' finished: 1/1 passed' in text
        rows = baseline_rows(text)
        case = {'exit': result.returncode, 'passed': passed,
                'outcome': rows or {},
                'log_sha256': hashlib.sha256(text.encode()).hexdigest()}
        expecting_fail = mode in opts.get('fail', ())
        if expecting_fail:
            case['expectation'] = 'fail: ' + opts['fail_reason']
            case['ok'] = (not passed)
        else:
            case['expectation'] = 'pass'
            case['ok'] = result.returncode == 0 and passed
        if mode in opts.get('rows_must', {}):
            for key, want in opts['rows_must'][mode].items():
                if (rows or {}).get(key) != want:
                    case['ok'] = False
                    case.setdefault('row_mismatch', {})[key] = {'want': want, 'got': (rows or {}).get(key)}
        blname = opts.get('_baseline_logs', {}).get(mode)
        if blname:
            previous = (opts['_baseline_dir'] / blname).read_text(errors='replace')
            prow = baseline_rows(previous)
            case['baseline_rows'] = prow
            case['baseline_log_sha256'] = hashlib.sha256(previous.encode()).hexdigest()
            case['byte_identical'] = text == previous
            if prow is not None and rows is not None and mode not in opts.get('rows_free', ()):
                if rows != prow:
                    case['ok'] = False
                    case['row_mismatch'] = {'baseline': prow, 'got': rows}
        cases[mode] = case
        print(f'  {name}/{mode}: {"OK" if case["ok"] else "MISMATCH"} '
              f'passed={passed} rows={rows}', flush=True)
    return cases


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--only', action='append', default=[],
                   help='run only these groups (repeatable; smoke tests)')
    args = p.parse_args()
    build = args.build.resolve()
    objects = sorted((build / 'CMakeFiles/OurCoreLib.dir').rglob('*.o')) + \
        sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    assert len(objects) >= 150, 'build objects missing'
    out = args.output.resolve()
    assert not out.exists(), f'{out} exists'
    out.mkdir(parents=True)
    report = {'build': str(build), 'groups': {}, 'total_cases': 0, 'ok': True}

    for name, dir_rel, tag, modes, opts in GROUPS:
        if args.only and name not in args.only:
            continue
        if opts.get('skip'):
            report['groups'][name] = {'kind': 'local', 'baseline': dir_rel,
                                      'skipped': True, 'reason': opts['skip'],
                                      'cases': {}, 'ok': True}
            print(f'{name}: SKIPPED ({opts["skip"][:60]}...)', flush=True)
            continue
        print(name, flush=True)
        baseline = ROOT / dir_rel
        opts = dict(opts)
        opts['_baseline_dir'] = baseline
        opts['_baseline_logs'] = {m: n for m in modes
                                  if (n := baseline_log_name(baseline, m, opts))}
        missing = [m for m in modes if m not in opts['_baseline_logs']]
        assert not missing, (name, 'baseline logs missing', missing)
        dest = out / name
        dest.mkdir()
        (dest / 'profile').mkdir()
        scenario = opts.get('scenario')
        if scenario:
            (dest / 'scenario.c').write_bytes((ROOT / scenario).read_bytes())
        else:
            source = (baseline / 'scenario.c').read_text()
            (dest / 'scenario.c').write_text(source.replace(str(baseline), str(dest)))
        # companion headers and data some fixtures generate or carry
        for extra in baseline.glob('*.h'):
            (dest / extra.name).write_bytes(extra.read_bytes())
        for extra in baseline.glob('*.txt'):
            (dest / extra.name).write_bytes(extra.read_bytes())
        (dest / 'profile/borg.txt').write_bytes((baseline / 'profile/borg.txt').read_bytes())
        cases = run_group(name, tag, modes, dest, objects, opts, build)
        report['groups'][name] = {'kind': 'local', 'baseline': dir_rel,
                                  'cases': cases,
                                  'ok': all(c['ok'] for c in cases.values())}
        report['total_cases'] += len(cases)

    for name, ref, opts in KIT_GROUPS:
        if args.only and name not in args.only:
            continue
        print(name, flush=True)
        opts = dict(opts)
        entries = git_ls(ref, 'docs/audit/c-reports/')
        kits = [d for d in entries
                if 'run-cases.py' in subprocess.check_output(
                    ['git', 'ls-tree', '--name-only', ref, d + '/'],
                    cwd=ROOT, text=True)]
        assert len(kits) == 1, (name, 'kit dir ambiguous', kits)
        prefix = kits[0]
        dest = out / name
        dest.mkdir()
        for path in subprocess.check_output(
                ['git', 'ls-tree', '-r', '--name-only', ref, prefix + '/'],
                cwd=ROOT, text=True).splitlines():
            rel = path[len(prefix):].lstrip('/')
            if not rel:
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git_show(ref, path))
        source = (dest / 'run-cases.py').read_text()
        match = TAG_RE.search(source)
        tag = match.group(1) or match.group(2)
        (dest / 'profile/borg.txt').write_bytes(git_show(ref, prefix + '/borg.txt'))
        # The kit's runner sets the scenario's cwd to the binary's parent;
        # the game resolves its data (gamedata/) from the cwd, so the
        # linked binary goes into the build's game directory like the
        # original observer builds did.
        binary = build / 'game' / ('m7kit-' + name)
        link = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                '-I' + str(ROOT / 'src/tests'), str(dest / 'scenario.c'),
                *map(str, objects), '-lm', '-o', str(binary)]
        with (dest / 'link.log').open('w') as log:
            subprocess.run(link, stdout=log, stderr=subprocess.STDOUT, check=True)
        env = dict(os.environ, LC_ALL='C.UTF-8')
        subprocess.run(['python3', str(dest / 'run-cases.py'), 'after', str(binary), str(dest)],
                       cwd=dest, env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.STDOUT, timeout=1200)
        rows = json.loads((dest / 'after-results.json').read_text())
        cases = {}
        for mode in sorted(rows):
            row = rows[mode]
            expecting_fail = opts.get('fail_all') or mode in opts.get('fail', ())
            if expecting_fail:
                ok = not row['passed']
            else:
                ok = row['exit'] == 0 and row['passed']
            case = {'exit': row['exit'], 'passed': row['passed'],
                    'outcome': row.get('outcome', {}),
                    'expectation': ('fail: ' + opts['fail_reason']) if expecting_fail else 'pass',
                    'ok': ok}
            for key, want in opts.get('rows_must', {}).get(mode, {}).items():
                if case['outcome'].get(key) != want:
                    case['ok'] = False
                    case.setdefault('row_mismatch', {})[key] = {'want': want, 'got': case['outcome'].get(key)}
            if (dest / f'after-{mode}.log').exists():
                text = (dest / f'after-{mode}.log').read_text(errors='replace')
                case['log_sha256'] = hashlib.sha256(text.encode()).hexdigest()
            cases[mode] = case
            print(f'  {name}/{mode}: {"OK" if ok else "MISMATCH"} '
                  f'passed={row["passed"]} rows={row.get("outcome")}', flush=True)
        report['groups'][name] = {'kind': 'kit', 'evidence_ref': ref, 'prefix': prefix,
                                  'cases': cases,
                                  'ok': all(c['ok'] for c in cases.values())}
        report['total_cases'] += len(cases)

    report['ok'] = all(g['ok'] for g in report['groups'].values())
    (out / 'regression-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    failed = [n for n, g in report['groups'].items() if not g['ok']]
    print(f'total cases: {report["total_cases"]}; failed groups: {failed or "none"}; '
          f'matrix ok: {report["ok"]}', flush=True)


if __name__ == '__main__':
    main()
