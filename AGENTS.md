# Tiny18 project rules

These rules apply only to this repository, not to global agent settings.

## Scope and publication

- Keyboard firmware is the main product; `addons/oled/` is optional. Preserve
  keyboard-only builds without requiring an OLED compiler or submodule.
- Preserve existing user changes. Do not flash devices, push, publish tags,
  create releases, or change visibility without explicit authorization.
- Purchased Gerber and case/switch-plate STL files, including modified or
  mirrored versions, must never enter the repository or release archives.
  Refer users to the purchase link in the README instead.
- Original additions use the root MIT license. Preserve upstream copyright
  and license notices, including file-specific terms in dependencies.

## Keymap and generated documentation

- `config/tiny18.keymap` is the keymap source of truth. Changes require chart,
  HTML and OLED-label regeneration together, followed by their tests.
- Run `docs/tools/make_chart.py` before `docs/tools/build_html.py`, then
  `docs/tools/make_oled_layers.py`. Use `uv run --no-project --with pillow`.
- Read the affected generated sections and their hand-written template
  captions; passing tests alone does not establish prose accuracy.
- Generators write within this repository. Website publication is separate
  work and must not be an implicit side effect of generation.

## Builds and versioned bundles

- After a successful keyboard build, prepare a complete new
  `firmware/vMAJOR.MINOR.PATCH/` bundle before calling the work complete.
- Include both UF2 halves, settings-reset UF2, optional OLED BIN, `VERSION.txt`,
  `SHA256SUMS`, and dependency license/attribution material. Use the same
  version for keyboard and OLED; never name a version folder after a run ID.
- Record both source commits, build date and Actions run ID. Local review
  builds must say that Actions was not run and disclose uncommitted sources.
- Before 1.0, use a minor bump for behavior changes and a patch bump for
  behavior-preserving fixes. Never overwrite a prior version bundle.
- Flash both keyboard halves from the same build. Use the matching OLED
  firmware only if a display is installed; firmware generation never flashes.
- Release automation creates drafts. Review licensing, checksums and hardware
  behavior before the separately authorized publication step.

## Commands and checks

- User-facing terminal commands use PowerShell 5.1: start with `Set-Location`,
  use `;` rather than `&&`, and use `if ($?)` for dependent commands.
- Tests: `uv run --no-project --with pillow python -m unittest discover -s docs/tools`
  and `uv run --no-project --with pyyaml python -m unittest discover -s tests`.
- The build/setup procedures are in `docs/build-and-release.md` and
  `docs/oled-setup.md`. `make` builds; `make flash` is an explicit device write.
