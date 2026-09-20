"""Input / output utilities — every disk read or write goes through here.

Centralising I/O lets us:

* Leave caching to consumers that key it by a validated release SHA.
* Wrap writes with lineage tracking automatically.
* Keep paths consistent (every caller imports from :mod:`thesis.paths`).
"""
