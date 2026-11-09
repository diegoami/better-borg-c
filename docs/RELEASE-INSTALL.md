# Installing a better-borg-c release

better-borg-c is [Angband](https://github.com/angband/angband) with the Borg
(the built-in automatic player) compiled in, plus bug fixes to the C Borg that
have each been verified on their own and reviewed as part of a milestone. It is
not an official Angband release.

Each release is built on one pinned upstream commit, not on an Angband release
tag. Release `4.2.6-impact-v9.1` is built on angband/angband
`e473720ed88a0f0c7ca66815cef3000eb4a38bc3` (master, 2026-10-27), which is
upstream 4.2.6 plus later development work. Its contents:

- the 98 carried fixes reviewed up to milestone 9
  ([review #380](https://github.com/diegoami/better-borg-c/issues/380),
  [package](https://github.com/diegoami/better-borg-c/blob/4.2.6-impact-v9.1/docs/measurement/IMPACT-MILESTONE9.md));
- the crash correction to patch 0099 (PR #398). Without it, every Necromancer
  game crashed at its first return to town;
- the munchkin-start-by-class default (PR #302).

It contains no other later change from the repository's main branch.

## Choose an asset

| Asset | Use it if |
| --- | --- |
| `better-borg-c-<version>-linux-x86_64.tar.gz` | You want to play on Linux right away, with the X11 front end |
| `better-borg-c-<version>-src.tar.gz` | You want to build it yourself, on any platform Angband supports |
| `better-borg-c-<version>-patch.tar.gz` | You have your own angband/angband git checkout and want to apply the changes to it |

Check each download against the release's checksums:

```sh
sha256sum -c SHA256SUMS --ignore-missing
```

## 1. Linux binary

Requirements: x86_64 Linux with X11 (`libX11`), and a C library at least as
new as the version stated in the release notes. The binary was built and tested
on Ubuntu 26.04. If it does not start on your system, build from the source
package instead (section 2).

```sh
tar xzf better-borg-c-<version>-linux-x86_64.tar.gz
cd better-borg-c-<version>-linux-x86_64
./angband -mx11
```

The directory is self-contained: saves, scores and `lib/user/borg.txt` stay
inside it, so you can move it anywhere.

## 2. Build from the source package

The source package is a plain Angband source tree with the changes already
applied. On Debian or Ubuntu:

```sh
sudo apt install build-essential cmake libx11-dev      # add libncurses-dev for a terminal front end
tar xzf better-borg-c-<version>-src.tar.gz
cd better-borg-c-<version>-src
cmake -B build -DCMAKE_BUILD_TYPE=Release -DSUPPORT_BORG=ON \
      -DSUPPORT_X11_FRONTEND=ON -DSC_INSTALL=ON \
      -DCMAKE_INSTALL_PREFIX="$HOME/games/better-borg-c"
cmake --build build --parallel
cmake --install build
"$HOME/games/better-borg-c/angband" -mx11
```

- For a terminal game, add `-DSUPPORT_GCU_FRONTEND=ON` and run with `-mgcu`.
- For other platforms and front ends (Windows, macOS, SDL2), follow
  Angband's own [build instructions](hacking/compiling.rst), which are
  `docs/hacking/compiling.rst` in the package. Keep `SUPPORT_BORG` on. The
  better-borg-c project tests only the Linux CMake build.

## 3. Apply the patch to your own checkout

```sh
git clone https://github.com/angband/angband.git
cd angband
git checkout e473720ed88a0f0c7ca66815cef3000eb4a38bc3
tar xzf /path/to/better-borg-c-<version>-patch.tar.gz
sh better-borg-c-<version>-patch/apply.sh .
```

Then build as in section 2, from the checkout's root.

- The patch is tested only on that base commit. `apply.sh` warns if your
  checkout is elsewhere, and stops without changing anything if the patch does
  not apply.
- It does **not** apply to the `4.2.6` release tag: the Borg sources changed
  too much after 4.2.6.
- `provenance/` lists each carried fix with its issue links and keeps the
  individual patch files for review. The single `.diff` is what you apply.

## Playing with the Borg

1. Start or load a character as usual. Use disposable characters: Borg games
   are not meant for your real saves, and they do not enter the high-score
   list.
2. Press **Ctrl-Z** and confirm. The Borg's prompt appears.
3. Press **z** to let it play. Press any key to stop it.
4. **Ctrl-X** saves and quits.

The Borg reads `borg.txt` from Angband's user directory (`lib/user/` in a
self-contained install). If the file is missing, the Borg writes one with
default values the first time it starts. This release defaults
`borg_munchkin_by_class = TRUE`: Warriors, Druids and Rangers stair-scum to
DL6 before playing normally. Set it to `FALSE` to give every class the plain
start. The in-game Borg command reference is `docs/hacking/borg.rst`.

## Problems and licence

Report problems at
[diegoami/better-borg-c issues](https://github.com/diegoami/better-borg-c/issues),
with the release version and your platform. Angband, the Borg and these changes
are distributed under Angband's licence terms; see `docs/copying.rst`
(`COPYING.rst` in the binary package).
