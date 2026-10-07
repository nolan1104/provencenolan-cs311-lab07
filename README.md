# Lab 7: The Collision Resolver

Full assignment: `Lab_07_The_Collision_Resolver.md`.

## Run
```bash
python compare_probing.py
```
Complete `hash_strategies.py`. The script inserts 50,000 keys into all
three maps, checks correctness (including tombstone-deletion edge
cases), then prints measured lookup time next to the theoretical
prediction from Part A for your write-up. Success Token prints once
every correctness check passes and no structure is pathologically slow.

**Read the docstring on `QuadraticProbingHashMap` before starting** --
quadratic probing over a power-of-2 table size doesn't reach every
slot and can report "table full" while empty slots still exist. Use a
prime table size and resize proactively (checked empirically while
building this: switching the reference from size 16 to prime sizing
fixed a real "table full" crash at just 20 keys).

## Submit
1. `Lab7_Theory.pdf` (or `.md`)
2. `hash_strategies.py`
3. The Success Token
