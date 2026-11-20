# Refugium Seed Creator

A keyboard-driven Wayland utility extracted from the entropy routines in
`mr-sitting` at `5de47c92329b9c90d1f2af82fb7f46ef010248b2`. It creates
an English BIP39 phrase with 128 or 256 entropy bits. There are no
Refugium seed letters, derived keys, wallet connections or sitting files.
The app never sends seed material to a file, clipboard or terminal.

The four draws are hand-checkable dice, SHA-256 hashed dice, coin flips,
and Entropia pills with coin flips. Use fair independent draws. The
hashed dice minimums are 50 and 100 rolls. For 12 words, the pill draw
uses seven flips and eleven independent pill words. For 24 words it uses
seven flips, twenty-two pill words and seven more flips. Use one space
between pill words and compact H/T or 1/0 groups for flips.

Record the displayed words on paper. Press Enter to hide them and choose
all words in order or 4–12 positions sampled without replacement. The
app uses Linux randomness to select check positions only. Wrong words
keep the current position active. Press F2 during the check to see the
same phrase again. Press Enter to hide it, then choose how many words
to check. Verification starts over. Escape or clicking × in the title bar
discards the session.

The utility requires whole-process memory locking before it accepts
entropy, disables core dumps, zeroizes the entered entropy and word
indices, and scrubs its shared display buffers when released and on
handled exits. The offline Weston session provides a 64 MiB lock
allowance. Weston and the display stack also see rendered pixels, so use
a trusted offline environment. A forced kill or power loss cannot run
the exit handler. The signet VM is a development preview for synthetic
draws.

## Build and integrate

Build on x86-64 Linux against Ubuntu Noble compatible libraries. Install
Rust and Cargo 1.92 or later, a C compiler, pkg-config, Wayland client and protocol
development files, Cairo development files, and xkbcommon development
files. From the repository root, run:

```sh
image/tools/refugium-seed/build .work/seed/refugium-seed
```

Pass the resulting binary to `scripts/build-rootfs.py sitting-stick
WORK --seed-creator BINARY` or pass it as the sixth argument to
`preview/signet/build`. The installer puts a sprout launcher in Weston’s
desktop panel. The binary requires Wayland, Cairo and xkbcommon.
