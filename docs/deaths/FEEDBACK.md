# Commenting on a death

Open [the death registry](README.md), select **Discuss** for the case, and leave
a comment on its linked GitHub investigation. Each report also has a
**Discuss this death** link. This is the durable discussion outside chat; a
comment does not need to be a code review or a new issue.

- [D0001: stegocentipede — discussion22](https://github.com/diegoami/better-borg-c/issues/22)
- [D0002: gallant — discussion34](https://github.com/diegoami/better-borg-c/issues/34)

Useful comment format (plain language is fine):

```text
Case: D0002
Observation: too many enemies for this character's level/resources.
Moment: room entry or the earliest visible dangerous group.
Suggestion/question: could it have avoided exposure or retreated earlier?
```

You can propose an explanation without proving it. The agent checks the case's
actual build, trajectory, inventory and what the Borg knew before acting.
Different builds and replay attempts keep their own identities. A terminal
picture alone does not prove how it entered the situation or whether a proposed
escape would work.

## When comments are checked

The consumer agent checks new or edited comments on every case investigation
and its linked open action issues at the start of each active work session and
before stopping. The checkpoint records which threads/latest comment IDs were
read and what needs follow-up. New owner comments receive an acknowledgement,
evidence triage and an action/finding link; acknowledgement does not mean the
underlying investigation is complete. Agent-generated receipts are not new
owner requests and do not require repeated replies.

This is part of active work. There is no unattended comment-processing agent
running between sessions. The weekly GitHub donor inventory collects fork
metadata; it does not analyze death comments. A new confirmed or credible bug
takes priority under the existing bug-first policy.

## From comment to action

1. **Record.** Keep the original GitHub comment. Chat feedback is copied to the
   case investigation with an owner-feedback heading and link before being
   treated as tracked. Add its link/summary to assessment.json's feedback list.
2. **Triage.** State what the recording supports, uncertainties, alternatives
   and whether this is a suspected bug, policy suggestion or expected behavior.
   Keep owner observations distinct from verified native facts.
3. **Track.** Add a specific action with a stable key and issue link to
   assessment.json. A focused new issue is useful for a reusable policy or
   separate mechanism; avoid another source report for the same defect.
4. **Investigate.** Use the earliest relevant known state and ordinary legal
   alternatives. Record resource costs, unavailable information, RNG divergence,
   failed/unfavorable results and whether the comparison is a diagnostic branch.
5. **Route.** Confirmed reusable original-C defects go to neo-angband-tracker
   with source207 ownership before source fix and separate consumer carry.
   Broader inventory/exposure policy suggestions remain proposals until assessed;
   an owner priority does not become a proved cause or an untested threshold.
6. **Report back.** Reply on the original investigation with the finding and
   experiment/fix links. Update the dossier assessment/actions and regenerate
   the registry. An investigation can end as not-a-bug or inconclusive; it is
   not silently marked fixed. Group shared actions across cases, not replays.

Use a plain action status such as **recorded**, **investigating**, **needs evidence**,
**proposed**, **verified**, **not a bug** or **inconclusive**, with a short reason.
Verification links to actual native evidence; a merged policy alone does not
prove a survival benefit. Original evidence/builds stay immutable when an
assessment evolves. Bug corrections always take priority.

## Current owner feedback

D0001: prioritize usable escape/healing/survival stock over spare gear. Its
terminal pack had19occupied/23slots (four free), and Phase Door was carried and
consumed earlier. [Proposal41](https://github.com/diegoami/better-borg-c/issues/41)
tracks reserve/retention/restock priorities; [22](https://github.com/diegoami/better-borg-c/issues/22)
tracks the actual stock/retreat/Speed decisions. Slot pressure or departure
with zero scrolls is not established from the terminal dump.

D0002: exposure to too many enemies too early for level3/resources.
[Action on34](https://github.com/diegoami/better-borg-c/issues/34#issuecomment-6685824152)
reconstructs first known danger and walk/flow/descent/teleport entry. A recorded
Phase Door precedes the critical crowd; intentional walking into it is not
assumed. No new crowd threshold or claimed rescue is implemented from one case.
