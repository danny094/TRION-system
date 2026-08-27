# TRION Home Filesystem MCP

This bundle is the single read-only owner for bounded file access below the
logical `/trion-home` root. It exposes list, path search, privacy-minimal
metadata, and UTF-8 read operations over stdio.

## Security contract

- Requests use root-relative paths only.
- Absolute paths, parent traversal, NUL bytes, and every symlink are rejected.
- File opens are descriptor-relative with no-follow semantics.
- Listing, search, and reads have hard limits; limits are never silently raised.
- The server exposes no write, delete, rename, permission, watch, shell, or exec operation.
- Visible results never contain the absolute root or host metadata.

`TRION_FILESYSTEM_ROOT` defaults to `/trion-home` and, when configured, must
still equal exactly `/trion-home`. Runtime mounting and P11 routing integration
are separate gates and are not part of this product slice.
