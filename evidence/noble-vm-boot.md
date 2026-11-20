# Ubuntu 24.04 development images in KVM

Two builder VMs produced byte-identical unsigned development images for each role. All four images booted from emulated USB under UEFI. The sitting stick displayed its memory-protection refusal before launching the wallet. The pinned ordinary helper lacks the strict memory behavior required for a complete sitting.

| Image | Bytes | SHA-256 from both builds |
| --- | ---: | --- |
| Node | 103825920 | `0c3c3ef8a7424bd3fca4dd273f4b14f75158934c0fe075fb9a529bb52d1a03b6` |
| Sitting stick | 302006784 | `eed8ad269b7d305def23516fe5e06ecc108fefa8ae4fc0c62ce4e4ec45478d1c` |

The first builder used the prepared Ubuntu role filesystems. The second bootstrapped fresh ones from the same authenticated Ubuntu snapshot, `20261118T000000Z`. Both used identical prebuilt kernel and application inputs. Each builder packed its own roots with the same development-only serial observer. A byte comparison and the rebuild component test passed for both roles. These results cover image assembly. Source-to-binary reproducibility of the kernel and wallet remains unmeasured.

## Boot observations

Each guest booted with 4 GiB of RAM, two emulated network adapters on an isolated virtual network, a writable internal disk and a second writable USB disk. Both writable disks retained their original SHA-256 after each boot. The node exposed both adapters under `6.12.118-mr-node` and reported Ubuntu Noble with `VARIANT_ID=refugium-node`. The stick exposed only `lo` under `6.12.118-mr-sitting`, reported `ID=mr-sitting-stick` and had no `/proc/swaps`.

Both roles ran systemd as PID 1. The root filesystem was read-only SquashFS. The guest mounted `/home`, `/run` and `/tmp` as tmpfs, and mounted `/var` as a writable overlay backed by `/run`.

The stick session reported soft and hard memory-lock limits of 67,108,864 bytes. The development image deliberately omits `/usr/bin/mr-sitting` until a strict build is available. The production session's preflight exited 2 before starting the wallet. The emulated display showed the following refusal on the first stick build:

> This stick could not verify its memory protection. Power off and boot a verified Refugium sitting stick.

## Separate diagnostic guest

A disposable diagnostic variant kept the production preflight enabled and ran three independent controls with public input. The ordinary helper was available only at a test path.

| Test | Observed result |
| --- | --- |
| Wallet rendering | The real `mr-gui` ran as UID 1000 under headless Weston, set the window title to “Refugium Wallet” and attached a Wayland surface buffer. |
| Whole-process locking | An unprivileged probe called `mlockall` with both `MCL_CURRENT` and `MCL_FUTURE` under the 64 MiB limit. A later 1 MiB allocation increased `VmLck` from 15,468 to 16,492 KiB. |
| Ordinary helper under an insufficient limit | With a 128 KiB limit, the real ordinary `mr-sitting` warned that locking failed and consumed all 23 bytes of a public invalid fixture. Its exit code of 2 followed input consumption. The strict stick requires refusal before reading input. |

The remaining application test needs a strict `mr-sitting` artifact. It must exercise the actual GUI-to-terminal launch, complete a public-fixture sitting, and observe the lock during live memory pressure, the closing check and cleanup. Physical hardware qualification remains separate.

The [VM harness](../tests/boot-development-image.py) boots an instrumented image and checks serial output and disk hashes. The [guest observer](../tests/guest/observe-image.py) records the kernel, interfaces, mounts, preflight status and application versions. The guest observer is enabled only in these development images. [Node receiver evidence](noble-receiver.md) covers the separate receiver installation tests.
