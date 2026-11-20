# Refugium OS

This repository holds the W3 design and local engineering work for the offline sitting stick and the base it shares with the secret-free node.

- [Base decision memo](B6-base-memo.md) records why both roles target Ubuntu 24.04 LTS and how the node obtains Blockstream Satellite.
- [Stick design draft](W3-stick-design-draft.md) covers the holder's journey, kernel, hardware, terminal, memory policy, media and updates.
- [W3 specification](design/SPEC_w3_stick.md) defines the proposed holder screens, refusals and acceptance tests.
- [Noble receiver evidence](evidence/noble-receiver.md) records the installation test and base filesystem builds.
- [Distribution research](design/agent-reports/base-options.md) records the package-index comparison.
- [Platform research](design/agent-reports/platform-evidence.md) records the kernel and terminal experiments.
- [Component observations](evidence/component-observations.txt) give the resolved kernel properties and the measured terminal history with its positive control.

The dated secure-memory rulings in the coordinator repository govern the stick. A released image requires complete image builds, boots and application integration evidence. Component measurements alone do not qualify an image.
