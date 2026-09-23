# Local firmware bundles

Generated bundles belong here as `vMAJOR.MINOR.PATCH/`. Each includes:

- `tiny18-right.uf2` and `tiny18-left.uf2`
- `settings-reset.uf2`
- `tiny18_layer.bin` (optional device, same release version)
- `VERSION.txt`, `SHA256SUMS`, and `LICENSES/`

The version directory and ZIP are ignored by Git. Distribute the approved ZIP
through a GitHub Release, not by committing generated firmware to the source
repository. Keep prior versions for rollback and never overwrite one.
See the [build and release procedure](../docs/build-and-release.md).
