# W3 image build plan

The [specification](SPEC_w3_stick.md) owns the acceptance observations and holder text. Each row below gives the failing control for its test. On good inputs the same command must exercise the corresponding positive path. An unavailable binary, image or physical device is a blocked test. A blocked test cannot count as an observed failure of the product or a pass.

Implement each group in order. First commit the test and its observed failure on the named wrong behavior. Commit the implementation separately. Keep raw diagnostics with synthetic fixtures only. Do not sign, flash a physical drive or use a holder wallet during development.

## Inputs and repeatable builds

| Test | Failing control | Command | Expected failure |
|---|---|---|---|
| profiles | Replace the stick role kernel with the node kernel. | `python3 tests/accept.py profiles` | `FAIL profiles: image roles share the wrong kernel` |
| inputs | Corrupt one required package after retrieval. | `python3 tests/accept.py inputs` | `FAIL inputs: required input failed authentication` |
| release | Use a trusted signature for the wrong image role. | `python3 tests/accept.py release` | `FAIL release: wrong release role accepted` |
| rebuild | Change one byte in the second complete image. | `python3 tests/accept.py rebuild` | `FAIL rebuild: clean builds differ` |

Use Canonical’s Noble release, updates and security pockets at the pinned timestamp for both roles. Run the terminal checks on Noble’s packaged executable. Keep Blockstream’s PPA on the node side when qualifying the W5 receiver packages.

## Kernel, boot and session

| Test | Failing control | Command | Expected failure |
|---|---|---|---|
| kernel | Boot with PCI Ethernet and virtio-net presented and the stock kernel. | `python3 tests/accept.py kernel` | `FAIL kernel: unexpected network interface` |
| identity | Remove the kernel suffix independently of the OS marker. | `python3 tests/accept.py identity` | `FAIL identity: wrong kernel identity accepted` |
| volatile | Attach an internal disk, swap and a preinserted transfer medium. | `python3 tests/accept.py volatile` | `FAIL volatile: persistent storage was used` |
| preflight | Present unreadable kernel evidence or a weakened helper. | `python3 tests/accept.py preflight` | `FAIL preflight: unsafe boot reached the wallet` |
| limits | Use the ordinary 8 MiB hard limit in the real session tree. | `python3 tests/accept.py limits` | `FAIL limits: session limit is not 67108864 bytes` |
| node | Substitute the sitting package set on the node foundation. | `python3 tests/accept.py node` | `FAIL node: secret-handling helper present on node` |

## Wallet, terminal and helper

| Test | Failing control | Command | Expected failure |
|---|---|---|---|
| components | Replace a pinned application with the same-named wrong executable. | `python3 tests/accept.py components` | `FAIL components: installed application differs from pin` |
| desktop | Omit the working folder-picker backend from the graphical session. | `python3 tests/accept.py desktop` | `FAIL desktop: wallet could not export the plan` |
| launch | Use a transfer path containing spaces and an uncleared GUI variable. | `python3 tests/accept.py launch` | `FAIL launch: terminal launch contract changed` |
| terminal | Open the terminal with ten history lines and a working accessibility observer. | `python3 tests/accept.py terminal` | `FAIL terminal: terminal exposed protected history or text` |
| strict | Run the ordinary helper under a limit too small for the whole process. | `python3 tests/accept.py strict` | `FAIL strict: helper accepted input before a strict lock` |
| pressure | Force a live allocation failure with the allocator unlock valve enabled. | `python3 tests/accept.py pressure` | `FAIL pressure: live lock released or cleanup failed` |
| closing | Refuse the closing thread after the hand-back was written. | `python3 tests/accept.py closing` | `FAIL closing: closing failure lost the safe waiting state` |
| end | Request handled termination at a secret-owning step and force one cleanup failure. | `python3 tests/accept.py end` | `FAIL end: cleanup report differs from the observed outcome` |
| sitting | Run the maximum supported complete signet sitting and real closing check. | `python3 tests/accept.py sitting` | `FAIL sitting: full sitting did not finish under the lock` |

## Media and qualification

| Test | Failing control | Command | Expected failure |
|---|---|---|---|
| select | Replace a requested removable partition before opening the mount. | `python3 tests/accept.py select` | `FAIL select: wrong or changed device accepted` |
| import | Import a malformed I1 followed by a valid I1 from a read-only source. | `python3 tests/accept.py import` | `FAIL import: unsafe import or source changed` |
| export | Try an unmatched hand-back and an I3 file under a public-looking name. | `python3 tests/accept.py export` | `FAIL export: private or unmatched file exported` |
| remove | Interrupt a transfer before the final file is synced and ejected. | `python3 tests/accept.py remove` | `FAIL remove: incomplete transfer reported success` |
| usb | Present an Ethernet gadget and a BOOTSEL device beside a real transfer volume. | `python3 tests/accept.py usb` | `FAIL usb: USB roles or mount policy differ` |
| hardware | Omit the target-machine run while retaining a passing VM run. | `python3 tests/accept.py hardware` | `FAIL hardware: physical support claim lacks a matching run` |

## Test boundaries

This is a new repository. Add the named acceptance cases under tests and retain the existing component measurements. The negative controls change one policy, result or input at a time. Parser tests use isolated fixture directories. Kernel, application, mount and transfer tests use disposable VM disks, an instrumented test process or an external observer. A release-mode binary and an actual graphical sitting exercise the normal entry point. Physical read-only device tests require the matching hardware. VM results cannot substitute for them.

## Coverage

[The coverage map](PLAN_w3_stick-coverage.tsv) includes each normative row, diagnostic and prose paragraph. `python3 scripts/check-plan.py` verifies exact quotes, row ownership and the command and failure names. Its negative control is `python3 scripts/check-plan.py --broken-control`, which exits 1 with `FAIL plan: coverage IDs differ from specification`. This gate checks the documents. The named acceptance cases test behavior.
