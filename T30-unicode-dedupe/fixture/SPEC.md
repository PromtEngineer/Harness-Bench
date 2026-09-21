# Identity dedup — canonicalization spec

people.tsv: header row `id\tname\temail`, then one record per line
(fields never contain tabs). Cluster records that denote the same person
under the CANONICAL KEY below, then write dedup.json.

## Canonical name key (apply in exactly this order)

1. Unicode-normalize to NFKC.
2. Remove every character in Unicode category Cf (format characters:
   zero-width space/joiner, soft hyphen, ...).
3. Replace every character in category Zs (space separators: NBSP,
   narrow NBSP, ideographic space, ...) with ASCII space U+0020, then
   collapse runs of spaces to one and strip leading/trailing spaces.
4. Apply str.casefold() (NOT lower(): ß must equal ss, etc).

## Canonical email key

Split at the LAST "@" into local and domain.

- domain: NFKC-normalize, casefold, strip. (Fullwidth domains fold to
  ASCII in NFKC — mind step order.)
- local: NFKC-normalize, remove Cf characters, casefold.
- Provider rule: if (and only if) the canonical domain is exactly
  "mailbox.example", additionally: truncate the local part at the first
  "+" (drop it and everything after), then remove ALL "." characters.

Canonical email = "<local>@<domain>".

## Clustering and output

Records cluster on the pair (name_key, email_key) — both must match.

dedup.json (workspace root):

    {"clusters": [[ids...], ...],
     "stats": {"rows": R, "clusters": C, "singletons": S,
               "merged_rows": R - C}}

- each cluster's ids sorted ascending; clusters sorted by first id
- every input id appears in exactly one cluster (singletons included)
- singletons = number of clusters of size 1
- all numbers are JSON integers
