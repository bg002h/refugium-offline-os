# Ubuntu Noble base and Blockstream Satellite

The install test used an Ubuntu Base 24.04.5 amd64 filesystem in a disposable VM. The Canonical CD-image signing fingerprint was 843938DF228D22F7B3742BC0D94AA3F0EFE21092. The tarball matched the signed checksum. APT authenticated the 20261118T000000Z Ubuntu snapshot and the Blockstream Noble PPA, signing fingerprint 5E4CECA7FA5F4561D5BF0397BA071931E00891B5.

APT installed the following five packages together with the default recommended dependencies. The package audit returned no findings.

- bitcoin-satellite 25.0.0.2.4-0ppa2~ubuntu24.04
- blockstream-satellite 2.5.1-0ppa1~ubuntu24.04
- gr-dvbs2rx 1.4.0-0ppa2~ubuntu24.04
- leandvb 2.0.1-0ppa2~ubuntu24.04
- tsduck 3.35.3258-0ppa2~ubuntu24.04

The installed programs reported blocksat-cli 2.5.1 and Bitcoin Satellite v0.2.4. The installed receiver library rejected the previous custom distribution ID. With the image recipe's ID=ubuntu, VERSION_CODENAME=noble and VARIANT_ID=refugium-node, the vendor CLI accepted the standalone, USB and SDR targets in dependency-installation dry runs. I then used the documented add-apt-repository command for ppa:blockstream/satellite and ran the real blocksat-cli dependency installer for all three targets with --btc. All completed, and the final package audit was empty. APT initially warned that the chroot lacked a terminal for its log. After mounting devpts, all three installer reruns were clean. The receiver executables were present and dpkg reported no unfinished configurations. The VM had no receiver hardware.

The W3 recipe also built fresh node and sitting root filesystems with Ubuntu-only APT inputs. Neither included the PPA. The node retained its Ubuntu identity. The stick used ID=mr-sitting-stick and did not contain bitcoin-satellite. The Noble Alacritty executable was 0.13.2. Under a host virtual Wayland compositor it retained eight grid rows for an eight-row window with the image policy and eighteen with the ten-line history control. The accessibility registry kept the GTK control and gained no terminal entry. Booted Noble release images, the full wallet sitting and physical receiver operation remain unqualified.
