"""Editable text buffer: chunked storage with a Fenwick index.

Same contract as the naive version; in-chunk edits are O(chunk) plus an
O(log n_chunks) index update, chunk splits/merges rebuild the index.
"""


class _Fenwick:
    def __init__(self, sizes):
        self.n = len(sizes)
        self.tree = [0] * (self.n + 1)
        for i, s in enumerate(sizes):
            self.add(i, s)

    def add(self, i, delta):
        i += 1
        while i <= self.n:
            self.tree[i] += delta
            i += i & (-i)

    def total(self):
        i, s = self.n, 0
        while i > 0:
            s += self.tree[i]
            i -= i & (-i)
        return s

    def find(self, pos):
        """Largest idx with prefix_sum(idx) <= pos; returns (idx, offset)."""
        idx = 0
        rem = pos
        bit = 1
        while bit * 2 <= self.n:
            bit *= 2
        while bit:
            nxt = idx + bit
            if nxt <= self.n and self.tree[nxt] <= rem:
                idx = nxt
                rem -= self.tree[nxt]
            bit //= 2
        return idx, rem


class Buffer:
    CHUNK = 8192

    def __init__(self, text=""):
        c = self.CHUNK
        self._chunks = [text[i:i + c] for i in range(0, len(text), c)] or [""]
        self._reindex()

    def _reindex(self):
        self._fen = _Fenwick([len(ch) for ch in self._chunks])

    def _length(self):
        return self._fen.total()

    def _locate(self, pos):
        idx, off = self._fen.find(pos)
        if idx >= len(self._chunks):          # pos == length
            idx = len(self._chunks) - 1
            off = len(self._chunks[idx])
        return idx, off

    def insert(self, pos, s):
        pos = max(0, min(pos, self._length()))
        idx, off = self._locate(pos)
        ch = self._chunks[idx]
        new = ch[:off] + s + ch[off:]
        if len(new) <= 2 * self.CHUNK:
            self._chunks[idx] = new
            self._fen.add(idx, len(s))
            return
        parts = [new[i:i + self.CHUNK] for i in range(0, len(new), self.CHUNK)]
        self._chunks[idx:idx + 1] = parts
        self._reindex()

    def delete(self, pos, n):
        length = self._length()
        pos = max(0, min(pos, length))
        n = max(0, min(n, length - pos))
        if n == 0:
            return
        idx, off = self._locate(pos)
        ch = self._chunks[idx]
        if off + n <= len(ch):                 # within one chunk
            self._chunks[idx] = ch[:off] + ch[off + n:]
            self._fen.add(idx, -n)
            if not self._chunks[idx] and len(self._chunks) > 1:
                del self._chunks[idx]
                self._reindex()
            return
        remaining = n
        self._chunks[idx] = ch[:off]
        remaining -= len(ch) - off
        j = idx + 1
        while remaining > 0 and j < len(self._chunks):
            cj = self._chunks[j]
            if len(cj) <= remaining:
                remaining -= len(cj)
                self._chunks[j] = ""
                j += 1
            else:
                self._chunks[j] = cj[remaining:]
                remaining = 0
        self._chunks = [c for c in self._chunks if c] or [""]
        self._reindex()

    def get_slice(self, pos, n):
        length = self._length()
        pos = max(0, min(pos, length))
        n = max(0, min(n, length - pos))
        if n == 0:
            return ""
        idx, off = self._locate(pos)
        out = []
        while n > 0 and idx < len(self._chunks):
            ch = self._chunks[idx]
            take = ch[off:off + n]
            out.append(take)
            n -= len(take)
            off = 0
            idx += 1
        return "".join(out)
