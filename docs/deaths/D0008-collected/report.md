# D0008: grey-mold retreat/re-exposure loop

[Owner feedback](https://github.com/diegoami/better-borg-c/issues/163#issuecomment-6714388294) · [Focused investigation212](https://github.com/diegoami/better-borg-c/issues/212) · [Overall assessment](overall-assessment.md)

Actual C46 source5c23742ced30, Human Priest CL1/depth1, seed1668846659, death10940. See unchanged record.json/build.json for immutable identity.

Original and stderr-only C diagnostic replay both VERIFIED. The priest repeatedly retreats onto the known upstairs then explores back into grey-mold melee, consumes three CLW, never attacks and leaves two Phase scrolls unused. Qualified diagnostics reproduce exception-mode cache entries being reused without danger evaluation in normal exploration, independently matching the related Rust report. Canonical source404 and consumer212 track the mechanism; source156 and shared159 remain separate contributing investigations.

No gameplay correction, successful alternative or population survival benefit claimed. Owner replay review complete; technical actions remain open.
