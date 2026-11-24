# Signet desktop preview

This x86-64 VM lets a tester run the wallet, the sitting TUI and Bitcoin Core together using public signet and test keys. It is an unsigned development image. The offline sitting stick and the separate node retain their own profiles.

## Test the sitting

The wallet connects to Core on guest loopback using the live user's RPC cookie. On a synced node the wallet opens at **Start**. Choose **Create a Refugium → Build my own**, add a creator and an **Everyday** refuge, then open **Seeds and keys**. Set at least one seed to be made or brought in the sitting. For example, select **Grown from root 1**. The wallet then shows **The sitting**. Choose the sitting folder and press **Export the plan and start the sitting**. Alacritty opens the W1T helper. A second completed sitting needs a fresh folder. The gold key in the top bar opens the full sample file from the live user's home. Choose **Copy line** or select text and press Ctrl+C, then use Ctrl+V in the wallet.

At the closing wait, this wallet build can read the hand-back. Its closing-file writer is still pending. To finish this test, press S in the TUI to skip the wallet check, press Enter to finish, then choose **Read the hand-back** in the wallet. The final wallet check remains unverified.

Guest clipboard transfers work within the desktop. The read-only boot disk supplies the fixture on every boot and the init script compares the whole copy. The live home, cookies and Core wallets live in RAM. Only the signet data disk persists. Each boot starts Core 31.1 with one configured P2P peer. QEMU forwards this peer to the host's loopback port 38333. RPC stays inside the guest. A host archival public-signet peer listening on that port must be available for a fresh guest to catch up. On a long initial sync the wallet may open its node status page.

## Launch a separate instance

Use Linux with KVM, session libvirt, QEMU with user networking, virt-manager and a matching pair of x86-64 OVMF firmware files. Obtain the boot disk from the coordinator. Compare its SHA-256 with the corresponding entry in [SHA256SUMS](SHA256SUMS). The following commands use a fresh state directory and create a sparse 56 GiB ext4 disk. It grows as Core downloads signet. Run the commands from this directory in a session without an existing domain named `refugium-signet`.

```sh
mkdir -m 700 signet-state
./make-chain.py signet-state/chain.ext4
./domain.py /path/to/refugium-signet.img signet-state/chain.ext4 signet-state \
    /path/to/OVMF_CODE.fd /path/to/OVMF_VARS.fd > signet-state/domain.xml
virsh -c qemu:///session define --validate signet-state/domain.xml
virsh -c qemu:///session start refugium-signet
virt-manager --connect qemu:///session --show-domain-console refugium-signet
```

The configured display is 1920 × 1200. The sitting terminal opens at about 95% of the display height, rounded to the closest row. The default width remains 88 columns when they fit. The connection status in the serial log contains public chain height, peer count and a wallet RPC availability flag.

## Rebuild the preview

The kit has three pinned binary inputs. The clipboard base supplies the Ubuntu Noble desktop, the complete example fixture, the GTK viewer and the two application binaries. The Core tar contains the runtime dependency closure for Bitcoin Core 31.1. The Linux 6.12.118 kernel uses [kernel.config](kernel.config). Obtain these three inputs from the coordinator. Their digests and the two installed application hashes are in [SHA256SUMS](SHA256SUMS).

Run the following inside a disposable root build VM with at least 10 GiB of workspace, systemd-ukify with its x86-64 EFI stub, static BusyBox, mtools, squashfs-tools, binutils, cpio, dosfstools, gzip, Python 3, a C compiler, pkg-config and GTK 3 development headers. The build verifies its inputs, extracts a fresh base, installs the signet profile and writes a new disk.

```sh
./build /path/to/clipboard-base.img /path/to/core.tar /path/to/signet-kernel \
    /usr/lib/systemd/boot/efi/linuxx64.efi.stub /path/to/new-preview.img
```

The repack assigns the signet preview its own GPT identifiers. Digest entries label the specific artifacts they cover.

The wallet source was `refugium-wallet@5da720457b7f6d2cc7e9cc375d5a20c4f00909b9`. The helper was `mnemonic-refugium@c532e250a7719d0359144b20f820417e1f74870c` with the [temporary strict-memory patch](strict-test.patch), built with Cargo feature `stick-strict-test`. The [key viewer source](public-keys.c) uses GTK 3. The session grants a 64 MiB soft and hard lock limit. The helper remains unqualified for real secrets. In particular, emergency allocation failure can bypass cleanup. The session's transfer and shutdown controls and complete stick acceptance are still open.

Weston displays a 3840 × 2160 slate-and-copper wallpaper using the Refugium Wallet shield. Minimize the wallet to see the entire desktop. The preview prepares the Xwayland socket directory immediately before Weston starts.

## Seed Creator

When the preview is built with the optional Seed Creator binary, the
sprout in the Weston panel opens a standalone English BIP39 generator.
Use synthetic entropy in this signet preview. Type 12 or 24, choose a
physical draw, and back up the words shown on screen. Enter hides the
phrase and starts the choice between checking every word and sampling
4–12 word positions. Press F2 during verification to review the phrase and start a fresh check. [Build and use the Seed Creator](../../image/tools/refugium-seed/README.md)

The preview can use a 70-pixel Weston panel with 64 × 64 launchers and
left-aligned wallet placement. Apply [the desktop patch](weston-desktop.patch)
to Weston 13.0.0, build the `clients/weston-desktop-shell` and
`desktop-shell/desktop-shell.so` Meson targets against Ubuntu Noble, and
set `WESTON_BUILD_DIR` to the absolute Meson build directory when running
the image recipe. The stock Weston build uses the compact launcher images.
