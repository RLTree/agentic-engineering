# Test Oracle Quality

A test is valuable only to the degree that it distinguishes relevant wrong behavior from right behavior.

Check:

- Does the test fail when the defect or a plausible mutation is introduced?
- Does it exercise the real contract rather than only a mock?
- Can it pass while the user journey, external effect, or integration is broken?
- Is the expected value independent from the implementation under test?
- Is the fixture representative and deterministic enough for its claim?
- Is the evidence bound to the exact candidate and environment?

Mocks are justified for unavailable, unsafe, costly, or nondeterministic dependencies, but critical mocked paths need representative contract or integration evidence. Track mutation score or defect-seeding results when the adequacy of a consequential suite is uncertain.

Evidence basis: R142, R139, R140.
