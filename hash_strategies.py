"""
Lab 7: The Collision Resolver -- starter.

Complete the three classes below. See
Lab_07_The_Collision_Resolver.md, Part B, for the full requirements.
"""

from typing import Generic, Hashable, List, Optional, Tuple, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")

_TOMBSTONE = object()  # sentinel marking a deleted open-addressing slot


class _ChainNode(Generic[K, V]):
    __slots__ = ("key", "value", "next")

    def __init__(self, key: K, value: V) -> None:
        self.key = key
        self.value = value
        self.next: Optional["_ChainNode[K, V]"] = None


class ChainedHashMap(Generic[K, V]):
    """Separate chaining: each bucket is a linked list of (key, value)."""

    def __init__(self, initial_size: int = 16) -> None:
        self._buckets: List[Optional[_ChainNode[K, V]]] = [None] * initial_size
        self._count = 0

    def __len__(self) -> int:
        return self._count

    def _append(self, key: K, value: V) -> None:
        index = hash(key) % len(self._buckets)
        new_node: _ChainNode[K, V] = _ChainNode(key, value)
        node = self._buckets[index]
        if node is None:
            self._buckets[index] = new_node
            return
        while node.next is not None:
            node = node.next
        node.next = new_node

    def _resize(self) -> None:
        old_buckets = self._buckets
        self._buckets = [None] * (2 * len(old_buckets))
        for head in old_buckets:
            node = head
            while node is not None:
                self._append(node.key, node.value)
                node = node.next

    def insert(self, key: K, value: V) -> None:
        """Insert, or update in place if `key` already exists. Resize (double + rehash) once load factor > 0.75."""
        index = hash(key) % len(self._buckets)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        if (self._count + 1) / len(self._buckets) > 0.75:
            self._resize()
        self._append(key, value)
        self._count += 1

    def get(self, key: K) -> V:
        """Return the value for `key`. Raise KeyError if missing."""
        index = hash(key) % len(self._buckets)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next
        raise KeyError(key)

    def delete(self, key: K) -> None:
        """Remove `key`. Raise KeyError if missing."""
        index = hash(key) % len(self._buckets)
        previous: Optional[_ChainNode[K, V]] = None
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                if previous is None:
                    self._buckets[index] = node.next
                else:
                    previous.next = node.next
                self._count -= 1
                return
            previous = node
            node = node.next
        raise KeyError(key)


class LinearProbingHashMap(Generic[K, V]):
    """Open addressing with linear probing and tombstone deletion."""

    def __init__(self, initial_size: int = 16) -> None:
        self._keys: List[object] = [None] * initial_size
        self._values: List[Optional[V]] = [None] * initial_size
        self._count = 0

    def __len__(self) -> int:
        return self._count

    def _find(self, key: K) -> int:
        home = hash(key) % len(self._keys)
        for offset in range(len(self._keys)):
            slot = (home + offset) % len(self._keys)
            current = self._keys[slot]
            if current is None:
                return -1
            if current is not _TOMBSTONE and current == key:
                return slot
        return -1

    def _place(self, keys: List[object], values: List[Optional[V]], key: K, value: Optional[V]) -> bool:
        home = hash(key) % len(keys)
        for offset in range(len(keys)):
            slot = (home + offset) % len(keys)
            if keys[slot] is None or keys[slot] is _TOMBSTONE:
                keys[slot] = key
                values[slot] = value
                return True
        return False

    def _resize(self) -> None:
        old_keys = self._keys
        old_values = self._values
        self._keys = [None] * (2 * len(old_keys))
        self._values = [None] * (2 * len(old_keys))
        for i in range(len(old_keys)):
            if old_keys[i] is not None and old_keys[i] is not _TOMBSTONE:
                self._place(self._keys, self._values, old_keys[i], old_values[i])

    def insert(self, key: K, value: V) -> None:
        """Resize (double + rehash) once load factor > 0.7."""
        slot = self._find(key)
        if slot != -1:
            self._values[slot] = value
            return

        if (self._count + 1) / len(self._keys) > 0.7:
            self._resize()
        self._place(self._keys, self._values, key, value)
        self._count += 1

    def search(self, key: K) -> V:
        """Return the value for `key`. Raise KeyError if missing."""
        slot = self._find(key)
        if slot == -1:
            raise KeyError(key)
        return self._values[slot]

    def delete(self, key: K) -> None:
        """Remove `key` using a tombstone (not None) so later probes don't stop early. Raise KeyError if missing."""
        slot = self._find(key)
        if slot == -1:
            raise KeyError(key)
        self._keys[slot] = _TOMBSTONE
        self._values[slot] = None
        self._count -= 1


def _next_prime(n: int) -> int:
    while True:
        is_prime = n >= 2
        divisor = 2
        while divisor * divisor <= n:
            if n % divisor == 0:
                is_prime = False
                break
            divisor += 1
        if is_prime:
            return n
        n += 1


class QuadraticProbingHashMap(Generic[K, V]):
    """
    Open addressing with quadratic probing and tombstone deletion.

    Pitfall to design around: with a power-of-2 table size, the probe
    sequence (idx + i^2) mod size does NOT reach every slot -- it can
    cycle through only about half of them, so the table can appear
    "full" and raise/loop forever even though empty slots exist
    elsewhere. Two standard fixes, pick one:
      (a) use a PRIME table size (so the quadratic sequence covers all
          slots whenever load factor < 1), or
      (b) resize proactively -- check load factor BEFORE attempting an
          insert's probe sequence, not only after a successful insert.
    """

    def __init__(self, initial_size: int = 17) -> None:
        self._keys: List[object] = [None] * initial_size
        self._values: List[Optional[V]] = [None] * initial_size
        self._count = 0

    def __len__(self) -> int:
        return self._count

    def _find(self, key: K) -> int:
        home = hash(key) % len(self._keys)
        for i in range(len(self._keys)):
            slot = (home + i * i) % len(self._keys)
            current = self._keys[slot]
            if current is None:
                return -1
            if current is not _TOMBSTONE and current == key:
                return slot
        return -1

    def _place(self, keys: List[object], values: List[Optional[V]], key: K, value: Optional[V]) -> bool:
        home = hash(key) % len(keys)
        for i in range(len(keys)):
            slot = (home + i * i) % len(keys)
            if keys[slot] is None or keys[slot] is _TOMBSTONE:
                keys[slot] = key
                values[slot] = value
                return True
        return False

    def _resize(self) -> None:
        old_keys = self._keys
        old_values = self._values
        new_size = _next_prime(2 * len(old_keys))
        while True:
            new_keys: List[object] = [None] * new_size
            new_values: List[Optional[V]] = [None] * new_size
            all_placed = True
            for i in range(len(old_keys)):
                if old_keys[i] is not None and old_keys[i] is not _TOMBSTONE:
                    if not self._place(new_keys, new_values, old_keys[i], old_values[i]):
                        all_placed = False
                        break
            if all_placed:
                break
            new_size = _next_prime(2 * new_size)
        self._keys = new_keys
        self._values = new_values

    def insert(self, key: K, value: V) -> None:
        """Resize (grow + rehash) once load factor > 0.7 -- see the pitfall note above."""
        slot = self._find(key)
        if slot != -1:
            self._values[slot] = value
            return

        if (self._count + 1) / len(self._keys) > 0.7:
            self._resize()
        while not self._place(self._keys, self._values, key, value):
            self._resize()
        self._count += 1

    def search(self, key: K) -> V:
        """Return the value for `key`. Raise KeyError if missing."""
        slot = self._find(key)
        if slot == -1:
            raise KeyError(key)
        return self._values[slot]

    def delete(self, key: K) -> None:
        """Remove `key` using a tombstone. Raise KeyError if missing."""
        slot = self._find(key)
        if slot == -1:
            raise KeyError(key)
        self._keys[slot] = _TOMBSTONE
        self._values[slot] = None
        self._count -= 1