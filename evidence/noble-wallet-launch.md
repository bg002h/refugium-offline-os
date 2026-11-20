# Offline wallet export and terminal launch on the Ubuntu stick

The Ubuntu Noble stick VM exported a public signet plan from the graphical wallet with Bitcoin Core offline. Selecting a folder required a session configuration change. The initial image had both portal packages installed, but the wallet's D-Bus session exposed no folder chooser.

The real wallet was built from `refugium-wallet@5da720457b7f6d2cc7e9cc375d5a20c4f00909b9`. A separate test session used the image's Weston configuration, live user and 64 MiB soft and hard lock limit. It put the ordinary W1T helper `5b439e23659e346edbdf7ef6c3f6d33f7e3d55eb` on a test-only search path. The production session still refused startup at preflight because its qualified strict helper was absent. The VM used an emulated USB boot disk, a virtio display and KVM. No seed was entered.

## Folder chooser and export

The baseline wallet reached **Seeds and keys**. Clicking **Choose the sitting folder** produced no dialog. The portal frontend was present on its session bus. Introspection of `org.freedesktop.portal.FileChooser` showed no `OpenFile` method and the GTK backend had no bus name.

With the [Refugium portal preference](../image/session/refugium-portals.conf) installed and the [session](../image/session/refugium-session.service) publishing Weston's socket name before starting D-Bus, the same check found both the method and the GTK backend. From the wallet's start screen, a test holder created a single-person Everyday refuge, opened the native chooser and selected **Holder's sitting folder**. The wallet reported that its node was unreachable. Pressing **Export the plan and start the sitting** created a file in the chosen directory under the live user's tmpfs home. The directory was UID 1000, mode 0700. The first two lines of the file identified a version 1 signet plan.

The [guest probe](../tests/guest/probe-wallet-chooser.py) queries the wallet's own session bus as the live user. Its output and the development boot observer's serial output are the inputs to `W3_DESKTOP_SERIAL=<capture> python3 tests/accept.py desktop --component`. The case failed on the baseline and passed on the configured session. This component result covers portal availability. The graphical export above was exercised separately.

## Terminal launch

With the DRM backend and Pixman renderer, the wallet started the real Alacritty process. Its parent was the wallet, both lock limits were 67,108,864 bytes, and a sentinel set only in the wallet environment was absent. The desktop disappeared at terminal startup in two boots. The session wrapper returned 139 in the instrumented repeat. The plan was still present in RAM. The observations identify the failed session, without a stack trace for the failing instruction.

Switching the same DRM backend to the GL renderer with software rendering enabled brought up Alacritty and the helper's signet start screen. The terminal was a child of the wallet. The helper ran as UID 1000 with soft and hard limits of 67,108,864 bytes. Its arguments contained separate plan and hand-back paths inside `/home/live/Holder's sitting folder`. Its environment contained exactly `LANG`, `PATH`, `TERM` and `XDG_RUNTIME_DIR`. Pressing Ctrl+Q, confirming with Y and pressing Enter closed the terminal. The original wallet process remained, with the sitting screen visible again.

The [public-fixture process observer](../tests/guest/observe-wallet-launch.py) records process identities, limits, the sentinel's presence and the expected public file arguments. Run it in a diagnostic guest while driving the wallet. For the positive control set `W3_GUI_ONLY=sentinel` on the test wallet session. The [launch check](../tests/cases/launch.py) rejects the failed session and a capture that carries the sentinel into the helper. The helper exited before secret entry. The remaining B07 acceptance work includes the session controls and power-off confirmation. A full production sitting still requires a qualified strict helper.

The successful journey ran twice, first with the kernel and initrd extracted from the diagnostic image, then from the same image as UEFI USB storage. OVMF failed to find a bootable device on one USB-port assignment. The repeat booted from USB port 1. The [USB-run serial excerpt](noble-wallet-launch.txt) can be used as the input to both component checks.
