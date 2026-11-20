# Signet desktop test results

The Ubuntu Noble preview ran a local unpruned Bitcoin Core 31.1.0 node and the normal wallet under UID 1000. On the populated disk, the wallet opened with **Synced · signet** without input. The guest and its upstream peer independently reported the same block at height 331651. The guest had one P2P peer, equal header and block heights, and a working wallet RPC call. A separate boot on an empty ext4 volume authenticated as the same wallet user and downloaded and validated blocks from genesis.

The clipboard base and the rebuilt guest contained the same two application binaries. The guest's full sample file matched the source byte for byte, including line breaks. Its boot script checks the copy into the volatile live home each time.

## Sitting terminal size

Weston's Wayland protocol supplied the logical output dimensions and Alacritty's decorated window geometry. The child PTY reported its grid with `stty size`. The comparison used empty test terminals in a separate VM. The 1280 × 800 check used a second Weston output inside the test VM.

| Logical display | Setting | Window | Visible grid |
| --- | --- | --- | --- |
| 1920 × 1200 | Previous default | 800 × 635 | 88 columns × 33 rows |
| 1920 × 1200 | Taller default | 800 × 1133 | 88 columns × 61 rows |
| 1280 × 800 | Taller default | 800 × 755 | 88 columns × 40 rows |

The terminal component gate also passed its original checks for history, clipboard escapes, IPC, live configuration reload and refused invocation shapes. Full stick qualification, including secure-memory cleanup and the transfer and power-off controls, remains open.
