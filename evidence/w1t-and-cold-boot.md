# Reviewed W1T helper and sitting-stick cold boots

The ordinary W1T candidate at `5b439e23659e346edbdf7ef6c3f6d33f7e3d55eb` completed a public signet sitting on the Noble stick kernel. It retained the ordinary-host memory policy. The W3 cold-boot storage test passed on a separately instrumented Noble image.

## What the reviewed helper did

The diagnostic image kept the production preflight enabled and placed the candidate at a separate test path. The public line-mode test ran as UID 1000, with a 64 MiB soft and hard lock limit and no privilege escalation. It used the deterministic W1 test answers for a single cold cosigner. The helper exited 0 and wrote a 401-byte public hand-back. The W3 utility built against the same revision of `mr-codec` accepted it with the original plan. It refused a different valid plan with the same ID. The accepted hand-back's SHA-256 was `c327dd318544937e8709f84ee5902a963be43ccceabbefc7dd92254304c0f12e`.

With a 128 KiB limit in the VM, the real `root` command warned that memory locking had failed, consumed all 23 public input bytes, then exited 2. I also exercised all four entry points directly in an isolated Linux network namespace at the same limit. Each consumed all 23 bytes after warning. The exit codes were 1 for `sit`, `verify` and `child` and 2 for `root`. This ordinary binary cannot satisfy the stick's requirement to refuse before input.

The W1T closing-worker regression passed. It forced a spawn failure, checked the existing hand-back and tried retry and quit, including a successful subsequent check. The production wallet-to-terminal path, whole-process locking through cleanup and the maximum-size sitting still need a strict helper.

Two additional signal runs used the same executable in an isolated Linux network namespace with a tmpfs runtime. The signal was sent after the plate file existed and the plate screen appeared. Each process reported 1,464 KiB locked immediately before the signal. After SIGTERM, the helper exited 1, the plate file and private directory were gone, and no hand-back existed. Its final text still claimed the seeds and passphrases had been wiped from the computer's memory. File removal does not establish that claim. After SIGKILL, the helper emitted no cleanup report and its plate file was still present in the private RAM directory when inspected. The test environment then discarded the RAM filesystem. [Recorded observations](w1t-public-controls.json)

## What survived a cold boot

Two fresh KVM processes booted the same diagnostic USB image under UEFI with the same writable disks attached. The stick identified both FAT32 partitions and a Linux swap partition. Both times its only block-backed mount was the read-only SquashFS root on `/dev/loop0`. Swap support was compiled out. The private runtime was on tmpfs, owned by UID 1000, and had mode 0700.

On each boot, the observer created and synced public markers in the sitting directory, private runtime, temporary directory and log directory. On the second boot all four markers were absent before the observer wrote new ones. The boot IDs differed. The full hashes of the internal disk and the USB transfer disk matched their initial values after **each** boot. The `volatile` acceptance case passed. [Both boot records and disk hashes](noble-cold-boot.json)

## Repeating the checks

The [review-bundle builder](../tests/build-reviewed-helper.py) takes a local mr repository, a full commit and a new work directory. It compiles the ordinary helper and the W3 public-file utility from the archive and locked vendor tree. The helper reports `unknown` for its Git stamp when built from this archive. The bundle records the full source revision separately. The checked-in [plan](../tests/fixtures/public-plan.txt) and [matching hand-back](../tests/fixtures/public-handback.txt) are public signet fixtures.

In a disposable build VM, stage a prepared development root with `sh tests/install-guest-observers.sh ROOT review BUNDLE` or `sh tests/install-guest-observers.sh ROOT storage` and pack the image with the existing W3 image recipe. For the review image, run the [USB boot harness](../tests/boot-development-image.py) with `--reviewed-helper`. For the storage image, set `W3_COLD_IMAGE` and run `python3 -B tests/accept.py volatile`. Setting `W3_COLD_EVIDENCE` to a new directory retains both consoles and the disk hashes. Neither diagnostic image is a release or a place for holder data.
