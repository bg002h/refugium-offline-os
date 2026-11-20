#!/bin/sh
# Install test-only observers into a prepared root directory before packing a diagnostic image.
set -eu
case "$#" in 2|3) ;; *) echo 'Usage: install-guest-observers.sh ROOT storage | ROOT review BUNDLE' >&2; exit 2;; esac
root=$(realpath "$1")
test "$root" != / && test -f "$root/etc/os-release" && test -f "$root/usr/lib/refugium/preflight.py" || exit 2
guest=$(CDPATH='' cd -- "$(dirname -- "$0")/guest" && pwd)
target="$root/usr/lib/refugium"
units="$root/etc/systemd/system"
enable_unit() {
    install -m644 "$guest/$1" "$units/$1"
    mkdir -p "$units/multi-user.target.wants"
    ln -sf "../$1" "$units/multi-user.target.wants/$1"
}

case "$2" in
    storage)
        test "$#" -eq 2 || exit 2
        install -m644 "$guest/observe-cold-boot.py" "$target/"
        extra=w3-storage-observe.service
        ;;
    review)
        test "$#" -eq 3 || exit 2
        bundle=$(realpath "$3")
        install -d "$target/review-control"
        for file in review-mr-sitting review-codec; do
            install -m755 "$bundle/$file" "$target/review-control/$file"
        done
        for file in public-plan.txt public-test-answers; do
            install -m644 "$bundle/$file" "$target/review-control/$file"
        done
        install -m644 "$guest/observe-reviewed-helper.py" "$target/review-control/"
        extra=w3-review-control.service
        ;;
    *) exit 2;;
esac
install -m644 "$guest/observe-image.py" "$target/vm-observe.py"
enable_unit w3-vm-observe.service
enable_unit "$extra"
