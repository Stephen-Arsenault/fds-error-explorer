# FDS Error Code Explorer

An interactive reference for the error codes shown by the **Famicom Disk System**
BIOS — the two-digit `ERR.xx` numbers that appear on a black screen when a disk
fails to load.

Pick a code and the panel explains, in plain language, what it means, what
triggers it, and what the television actually shows. Colour groups the codes by
where the fault lives: the drive, the disk you inserted, the data on it, or the
software.

**→ [Open the guide](https://stephen-arsenault.github.io/fds-error-explorer/)**

## What makes this different from the usual code list

The behaviour is traced from the BIOS ROM itself rather than copied from an
existing table, which turned up several things the circulating lists get wrong:

- **`$0A`–`$0F`, `$35` and `$40` cannot occur.** No routine in the ROM produces
  them. `$35` is not an error at all — it is the warm-boot signature the BIOS
  writes to `$0102`. `$40` ("not all files loaded") has no raise site: a short
  load returns success with a smaller count in `Y`, and detecting it is the
  calling program's job.
- **Several codes have more than one cause.** `$01` is raised at three separate
  points, so "no disk at start-up" and "disk pulled mid-load" are the same
  number. `$05` covers four distinct header fields. `$26` covers four different
  comparison sources.
- **`$20` is not a disk error.** It is a licensing check: the BIOS inspects the
  screen the loaded game has drawn and refuses to start it if Nintendo's
  copyright notice is missing. It runs *after* a completely successful load, yet
  still shows the generic `DISK TROUBLE` banner.
- **Most wrong-disk codes cannot appear at power-on.** The BIOS's own disk-ID
  template at `$EFF5` is `FF FF FF FF FF FF 00 00 FF FF`, and `$FF` means
  "don't care" — so only the side (`$07`) and disk-number (`$08`) checks are
  enforced during start-up.
- **Only four codes get words on screen.** The renderer looks the code up in a
  four-entry table (`$01`, `$02`, `$07`, `$08`); everything else displays a
  blank message line and a bare number.

Each entry carries the raise site and the literal condition, so any claim can be
checked against a disassembly.

## Sources

Program behaviour is from static analysis of one 8&nbsp;KB BIOS image; nothing
was executed or emulated. Physical details of the media, drive mechanism and
connector are not derivable from the ROM and come from the
[NESdev Wiki](https://www.nesdev.org/wiki/Family_Computer_Disk_System) and
community hardware documentation.

## Building

`index.html` is generated. Edit `src/page.html` — which is the page as an HTML
fragment, with no document shell — then run:

```sh
python3 build.py
```

The build step adds the doctype, `<head>`, charset, Open Graph tags and favicon.
Most importantly it adds the viewport meta tag: without it, phone browsers
assume a ~980px viewport and none of the mobile breakpoints fire.

There are no dependencies and no external requests — the page is a single
self-contained file.

## Licence

The page and its text are MIT licensed; see [LICENSE](LICENSE). The error
descriptions describe the behaviour of Nintendo's BIOS, which is not included
here in any form.
