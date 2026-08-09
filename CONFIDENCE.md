# Claim-state matrix

> **Superseded aggregate model:** the Version 3 score is historical lineage, not
> current authority. This matrix and `docs/foundations/current-2026-08-08.md`
> replace it with separate, noncompensatory claims.

This document replaces the prior aggregate confidence score. Unlike evidence classes are not added into one probability or release-quality number. Each claim needs its own passed stage on the exact candidate.

| Claim | Required evidence | Current state | Maximum current statement |
|---|---|---|---|
| Package identity and structure | A1 executed structural checks | Candidate-bound | Observed only when the exact candidate's A1 release command passes. |
| Activation and abstention | AQ held-out routing evaluation | Unobserved | No activation claim. |
| Isolated advice value | AS frozen adviser and builder evaluation | Unobserved | No advice-value claim. |
| Two-decision composition | AC held-out composition evaluation | Unobserved | No composition claim. |
| Archive, host, and protocol journey | AH exact archives and clean-host checks | Unobserved | No installation, discovery, coexistence, or protocol claim. |
| Field usefulness | AF authorized field evidence | Unobserved | No user, product, or field-value claim. |

Source review, historical inventory counts, schema checks, static source checks, and validator coverage can support only the exact structural or research claim they observe. They cannot compensate for a missing activation, host, or field stage. The current research decision authority is `docs/foundations/current-2026-08-08.md`.

## Release interpretation

A structural release, where allowed by package policy, may state only that the named candidate passed its recorded structural checks. It must retain every unobserved row above. A later stage may add its own observed claim; it does not retroactively turn earlier structural evidence into behavioral evidence.
