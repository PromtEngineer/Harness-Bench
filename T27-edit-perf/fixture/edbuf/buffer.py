"""Editable text buffer used by driver.py.

Contract (driver.py and the grader depend on it):
- Buffer(text) starts with the given text.
- insert(pos, s): insert s at pos; pos is clamped to [0, len].
- delete(pos, n): delete up to n chars at pos; pos clamped to [0, len],
  n clamped to len - pos.
- get_slice(pos, n) -> str: read up to n chars at pos, same clamping.

You may reimplement this class however you like as long as the contract
holds. The current implementation is correct but far too slow for the
full workload.
"""


class Buffer:
    def __init__(self, text=""):
        self._text = text

    def _clamp(self, pos):
        return max(0, min(pos, len(self._text)))

    def insert(self, pos, s):
        pos = self._clamp(pos)
        self._text = self._text[:pos] + s + self._text[pos:]

    def delete(self, pos, n):
        pos = self._clamp(pos)
        n = max(0, min(n, len(self._text) - pos))
        self._text = self._text[:pos] + self._text[pos + n:]

    def get_slice(self, pos, n):
        pos = self._clamp(pos)
        n = max(0, min(n, len(self._text) - pos))
        return self._text[pos:pos + n]
