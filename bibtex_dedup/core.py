"""Core logic: a small BibTeX parser plus duplicate detection and merging."""
import re
import unicodedata
from difflib import SequenceMatcher

_ENTRY_START = re.compile(r"@(\w+)\s*([{(])")
_FIELD_NAME = re.compile(r"\s*,?\s*([\w\-:.]+)\s*=\s*")
_BARE_VALUE = re.compile(r"[^,\s}]+")


def _read_balanced(text, start, open_ch, close_ch):
    """Return the index just after the delimiter closing the one at text[start - 1]."""
    depth = 1
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("Unbalanced delimiters in BibTeX input")


def _parse_fields(body):
    fields = {}
    i, n = 0, len(body)
    while i < n:
        m = _FIELD_NAME.match(body, i)
        if not m:
            break
        name = m.group(1).lower()
        i = m.end()
        if i < n and body[i] == "{":
            end = _read_balanced(body, i + 1, "{", "}")
            value, i = body[i + 1:end - 1], end
        elif i < n and body[i] == '"':
            j, depth = i + 1, 0
            while j < n:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                elif body[j] == '"' and depth == 0:
                    break
                j += 1
            value, i = body[i + 1:j], j + 1
        else:
            m2 = _BARE_VALUE.match(body, i)
            value = m2.group(0) if m2 else ""
            i = m2.end() if m2 else i + 1
        fields[name] = re.sub(r"\s+", " ", value).strip()
    return fields


def parse_bibtex(text):
    """Parse BibTeX text into a list of dicts with keys 'type', 'key' and 'fields'.

    @comment, @preamble and @string blocks are skipped.
    """
    entries = []
    pos = 0
    while True:
        m = _ENTRY_START.search(text, pos)
        if not m:
            break
        etype = m.group(1).lower()
        close_ch = "}" if m.group(2) == "{" else ")"
        end = _read_balanced(text, m.end(), m.group(2), close_ch)
        body = text[m.end():end - 1]
        pos = end
        if etype in ("comment", "preamble", "string"):
            continue
        key, _, rest = body.partition(",")
        entries.append({"type": etype, "key": key.strip(), "fields": _parse_fields(rest)})
    return entries


def normalize_title(title):
    """Lowercase and strip accents, braces, LaTeX commands and punctuation."""
    t = re.sub(r"\\[a-zA-Z]+\s*", "", title or "")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def normalize_doi(doi):
    """Normalize a DOI: drop resolver prefixes and 'doi:', lowercase."""
    d = (doi or "").strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    if d.startswith("doi:"):
        d = d[4:]
    return d.strip()


def _first_author_surname(entry):
    first = entry["fields"].get("author", "").split(" and ")[0].strip()
    if "," in first:
        return normalize_title(first.split(",")[0])
    parts = first.split()
    return normalize_title(parts[-1]) if parts else ""


def similarity(a, b):
    """Return a 0..1 similarity score between two entries' normalized titles."""
    ta = normalize_title(a["fields"].get("title"))
    tb = normalize_title(b["fields"].get("title"))
    if not ta or not tb:
        return 0.0
    return SequenceMatcher(None, ta, tb).ratio()


def is_duplicate(a, b, threshold=0.9):
    """Decide whether two entries describe the same work.

    Matching DOIs -> duplicate; two different DOIs -> distinct; otherwise the title
    similarity must reach `threshold` with no conflicting year or first-author surname.
    """
    da, db = normalize_doi(a["fields"].get("doi")), normalize_doi(b["fields"].get("doi"))
    if da and db:
        return da == db
    if similarity(a, b) < threshold:
        return False
    ya, yb = a["fields"].get("year"), b["fields"].get("year")
    if ya and yb and ya != yb:
        return False
    sa, sb = _first_author_surname(a), _first_author_surname(b)
    return not (sa and sb and sa != sb)


def find_duplicates(entries, threshold=0.9):
    """Group duplicate entries; returns lists of indices (only groups of size >= 2)."""
    parent = list(range(len(entries)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            if find(i) != find(j) and is_duplicate(entries[i], entries[j], threshold):
                parent[find(j)] = find(i)
    groups = {}
    for i in range(len(entries)):
        groups.setdefault(find(i), []).append(i)
    return [g for g in groups.values() if len(g) > 1]


def merge_entries(group):
    """Merge duplicates: keep the first key and type, fill in missing fields and
    prefer the longest (most complete) value when entries disagree."""
    base = {"type": group[0]["type"], "key": group[0]["key"], "fields": dict(group[0]["fields"])}
    for other in group[1:]:
        for k, v in other["fields"].items():
            if len(v) > len(base["fields"].get(k, "")):
                base["fields"][k] = v
    return base


def deduplicate(entries, threshold=0.9):
    """Return (deduplicated entries, report) where report lists the merged key groups."""
    drop, merged_at, report = set(), {}, []
    for g in find_duplicates(entries, threshold):
        merged_at[g[0]] = merge_entries([entries[i] for i in g])
        drop.update(g[1:])
        report.append([entries[i]["key"] for i in g])
    out = [merged_at.get(i, e) for i, e in enumerate(entries) if i not in drop]
    return out, report


def format_entry(entry):
    """Serialize an entry dict back to BibTeX."""
    lines = ["@%s{%s," % (entry["type"], entry["key"])]
    for k, v in entry["fields"].items():
        lines.append("  %s = {%s}," % (k, v))
    lines.append("}")
    return "\n".join(lines)
