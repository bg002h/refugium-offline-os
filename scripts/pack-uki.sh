#!/bin/sh
# Assemble a prepared root filesystem in the disposable build VM.
set -eu
[ "$#" -eq 5 ] || { echo 'Usage: pack-uki.sh ROLE ROOTFS KERNEL UKI-STUB OUTPUT' >&2; exit 2; }
role=$1
case "$role" in sitting-stick|node) ;; *) exit 2;; esac
rootfs=$(realpath "$2")
kernel=$(realpath "$3")
stub=$(realpath "$4")
out=$(realpath -m "$5")
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Output already exists.' >&2; exit 2; }
[ "$(id -u)" -eq 0 ] && systemd-detect-virt --quiet --vm || { echo 'A dedicated build VM is required.' >&2; exit 2; }
[ -f "$rootfs/etc/os-release" ] && [ -f "$rootfs/sbin/init" ] && [ -f "$kernel" ] && [ -f "$stub" ] || exit 2
: "${SOURCE_DATE_EPOCH:?set the pinned build epoch}"
export LC_ALL=C TZ=UTC
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
work=$(mktemp -d "${TMPDIR:-/var/tmp}/refugium-uki.XXXXXXXX")
new=$work/init
mkdir -p "$new"/bin "$new"/dev "$new"/proc "$new"/sys "$new"/newroot "$work"/efi/EFI/BOOT
cp /usr/bin/busybox "$new/bin/busybox"
for applet in mount losetup mkdir chmod chown sleep switch_root; do ln "$new/bin/busybox" "$new/bin/$applet"; done
cp "$repo/image/boot/init" "$new/init"
env -u SOURCE_DATE_EPOCH mksquashfs "$rootfs" "$new/system.squashfs" -noappend -no-progress -no-xattrs -comp xz -all-time "$SOURCE_DATE_EPOCH" -mkfs-time "$SOURCE_DATE_EPOCH" -processors 2 >/dev/null
find "$new" -exec touch -h -d "@$SOURCE_DATE_EPOCH" '{}' +
(cd "$new" && find . -mindepth 1 -printf '%P\0' | sort -z | cpio --null -o --quiet --reproducible --owner=0:0 -H newc) > "$work/newc"
gzip -1 -n < "$work/newc" > "$work/live-initrd.gz"
ukify build --linux="$kernel" --initrd="$work/live-initrd.gz" --stub="$stub" --os-release="@$rootfs/etc/os-release" --cmdline='quiet ro console=ttyS0,115200 console=tty0 rdinit=/init systemd.gpt_auto=no noresume' --output="$work/efi/EFI/BOOT/BOOTX64.EFI"
bytes=$(stat -c '%s' "$work/efi/EFI/BOOT/BOOTX64.EFI")
mib=$(( (bytes + 1048575) / 1048576 + 32 ))
[ "$mib" -ge 72 ] || mib=72
truncate -s "${mib}M" "$work/esp.fat"
mkfs.fat --invariant -F 32 -i 57335331 -n REFUGIUM "$work/esp.fat" >/dev/null
find "$work/efi" -exec touch -h -d "@$SOURCE_DATE_EPOCH" '{}' +
mcopy -smp -i "$work/esp.fat" "$work/efi/EFI" ::/
python3 "$repo/scripts/assemble-esp.py" "$role" "$work/esp.fat" "$out"
