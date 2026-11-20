# Refugium OS

This repository holds the W3 design and local engineering work for the offline sitting stick and the base it shares with the secret-free node.

- [Base decision memo](B6-base-memo.md) records why both roles target Ubuntu 24.04 LTS and how the node obtains Blockstream Satellite.
- [Stick design draft](W3-stick-design-draft.md) covers the holder's journey, kernel, hardware, terminal, memory policy, media and updates.
- [W3 specification](design/SPEC_w3_stick.md) defines the proposed holder screens, refusals and acceptance tests.
- [Build plan](design/PLAN_w3_stick.md) and [coverage map](design/PLAN_w3_stick-coverage.tsv) give the proposed test-first build sequence.
- [Noble receiver evidence](evidence/noble-receiver.md) records installation on a clean Ubuntu filesystem and the two image base builds.
- [Noble VM boot evidence](evidence/noble-vm-boot.md) records two independent builds of each USB image, four UEFI boots, the stick's startup refusal and the separate wallet and memory tests.
- [Reviewed W1T helper and cold boots](evidence/w1t-and-cold-boot.md) records a public signet sitting with the W1T review binary, its low-limit and signal behavior, and the two-boot storage test.
- [Distribution research](design/agent-reports/base-options.md) records the package-index comparison.
- [Platform research](design/agent-reports/platform-evidence.md) records the kernel and terminal experiments.
- [Kernel boot observations](evidence/kernel-boot.txt) record the guest with two network adapters presented and a real unprivileged memory-lock check.
- [Component observations](evidence/component-observations.txt) give the resolved kernel properties and the measured terminal history with its positive control.

The dated secure-memory rulings in the coordinator repository govern the stick. A released image requires complete image builds, boots and application integration evidence. Component measurements alone do not qualify an image.

The original spec checkpoint `w3-spec-v1` used Debian 13. The current spec review checkpoint is `w3-spec-v3`, targeting Ubuntu 24.04 LTS and assigning live satellite reception to the user. The earlier unsigned diagnostic disk and terminal measurements used Debian. The diagnostic deliberately omits a qualified strict helper. The released stick, full wallet journey and physical support matrix still require their own results.
