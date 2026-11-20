# Refugium OS

This repository holds the W3 design and local engineering work for the offline sitting stick and the base it shares with the secret-free node.

- [Base decision memo](B6-base-memo.md) gives the proposed B6 ruling and the node packaging cost.
- [Stick design draft](W3-stick-design-draft.md) covers the holder's journey, kernel, hardware, terminal, memory policy, media and updates.
- [W3 specification](design/SPEC_w3_stick.md) defines the proposed holder screens, refusals and acceptance tests.
- [Build plan](design/PLAN_w3_stick.md) and [coverage map](design/PLAN_w3_stick-coverage.tsv) give the proposed test-first build sequence.
- [Distribution research](design/agent-reports/base-options.md) records the package-index comparison.
- [Platform research](design/agent-reports/platform-evidence.md) records the kernel and terminal experiments.
- [Kernel boot observations](evidence/kernel-boot.txt) record the guest with two network adapters presented and a real unprivileged memory-lock check.
- [Component observations](evidence/component-observations.txt) give the resolved kernel properties and the measured terminal history with its positive control.

The dated secure-memory rulings in the coordinator repository govern the stick. A released image requires complete image builds, boots and application integration evidence. Component measurements alone do not qualify an image.

The spec review checkpoint is `w3-spec-v1`. Later local commits are development work. The first Debian live-build root and unsigned UEFI diagnostic disk were assembled in a VM. The diagnostic deliberately omits a qualified strict helper. The released stick, full wallet journey and physical support matrix still require their own results.
