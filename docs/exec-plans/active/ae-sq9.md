# AE-SQ9 clean-process qualification successor

Status: **TERMINAL — SQ9-F2A NOT_PASS; SQ9-AR**
Program: `AE-SQ9`
Candidate: `AE-SQ9-SLEC-9`
Machine authority: `evals/ae-sq9/program-authority.json`
Terminal date: 2026-08-15, America/Los_Angeles
Claim ceiling: exact F1G custody plus aggregate-only author-route failure and terminal custody only

## 0. Terminal disposition

SQ9 is closed at commit `f0c8f4436a68657ead041bcd216971f0c93593b5`
on edge `SQ9-F2A:NOT_PASS->SQ9-AR`. F1A, manifest-only F1B, and
taskless F1G completed. Before a lawful two-author F2A could be formed, one
author route disclosed access outside the frozen isolation boundary. The
route therefore failed custody before pair validation. The other author
stopped without creating a split artifact, and no author object was admitted
to the canonical lineage.

The aggregate-only terminal record is
`evals/ae-sq9/ar/terminal-decision.json`, raw SHA-256
`350836e316378e41e067915f4d13be3e5c7fa1f766c45edb55a1f1404aef85ac`.
Its exact last completed phase is `SQ9-F1G`; `aggregate_result` is null. No
pair validation, F2A, F2B, F2G, F3-F6, one-shot state, result, handoff,
canary, batch, or model call occurred. The failed route is consumed: no retry,
replacement, replay, repair, refreeze, resume, or reuse is permitted.

## 1. Successor isolation capability gate

A successor based on hermetic authoring requires an execution surface that
can prove both an allowed positive path and the forbidden read/write reds.
The zero-task host probe tested Apple Seatbelt, container, and chroot
capabilities without opening repository corpus material or making model or
network calls.

`/usr/bin/sandbox-exec` was present, but both the managed-sandbox attempt and
the one owner-authorized elevated synthetic attempt aborted before child
execution. On the elevated attempt the allowed sentinel read failed, the sole
authorized output write failed, and the exact output bytes were absent. The
apparent red denials are non-evidence because every sandboxed child aborted.
Docker socket access and unprivileged chroot were unavailable, and no other
supported offline isolation runtime was present.

Therefore the capability gate is `NOT_PASS`, not an implementation defect to
work around. No AE-SQ10 plan, authority, candidate, branch, corpus, or runtime
artifact is created. A future successor requires a separate owner
authorization after a capable execution surface demonstrates one positive
read, one exact output write, and all forbidden-path reds through the same
enforcement boundary.

## 2. Preserved historical contract

The original SQ9 F0 authority remains immutable at commit
`88c1b04dc049ab7656e811df9bc3f9e33276f778`; its active-plan bytes have raw
SHA-256 `7d01de0811e2eea877d21206b42626ec3d447702c63d573ac3b8c33570b728f1`.
That authority specified a fresh candidate, manifest-only F1B, taskless F1G,
independent 2 x 20 authoring, receipt-only F2G, zero-model preflight, four-call
canary, conditional 320-call batch, global logical AND, aggregate-only
outcomes, and zero retry. The terminal transition does not reinterpret or
weaken those requirements; it records that the F2A entry gate did not pass.

SQ9 has no next phase. Its terminal and interface provenance may inform a
separately authorized successor, but no SQ9 active-role, author, split,
corpus, task, case, label, schedule, F2, result, or execution byte may be
reused. This closeout proves neither general host isolation nor any provider,
model, product, field, production, security, release, publication, promotion,
or effect claim.
