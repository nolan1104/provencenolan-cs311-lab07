"""
Lab 7: The Collision Resolver -- verification suite.

Run: python compare_probing.py
Prints the Success Token only if every check below passes.

Note on the "theoretical bounds" check: Part A derives closed-form
comparison-count formulas, but those formulas require counting
probes/chain-hops *inside* get()/search() -- something a black-box
test can't observe without dictating extra instrumentation beyond
what Part B actually requires. Instead, this script prints the
theoretical prediction (computed from each structure's real final
load factor) next to a measured average WALL-CLOCK lookup time, for
you to cross-reference in your Part A write-up, and gates the token on
a looser, still-meaningful sanity check: no structure should be
dramatically (10x+) slower per lookup than the others, which would
indicate an accidental O(n) scan instead of real O(1)-ish hashing.
"""

import base64
import hashlib
import math
import random
import sys
import timeit

from hash_strategies import ChainedHashMap, LinearProbingHashMap, QuadraticProbingHashMap

ASSIGNMENT_ID = "LAB07"
N_KEYS = 50_000


def get_student_id() -> str:
    """Prompt for the student's USI username; baked into the Success Token
    so a copied/shared token decodes to someone else's name, not yours."""
    student_id = input("Enter your USI username (e.g. cwill): ").strip()
    while not student_id:
        student_id = input("Username cannot be blank. Enter your USI username: ").strip()
    return student_id


def generate_token(assignment_id: str, student_id: str) -> str:
    digest = hashlib.sha256(f"CS311-{assignment_id}-{student_id}-VERIFIED".encode()).hexdigest()[:16]
    raw = f"CS311|{assignment_id}|{student_id}|PASS|{digest}"
    return base64.b64encode(raw.encode()).decode()


def print_success_banner(assignment_id: str) -> None:
    student_id = get_student_id()
    token = generate_token(assignment_id, student_id)
    print("\n" + "=" * 60)
    print(f"  ALL CHECKS PASSED -- {assignment_id}")
    print(f"  STUDENT: {student_id}")
    print("  SUCCESS TOKEN (paste this into Blackboard):")
    print(f"  {token}")
    print("=" * 60 + "\n")


def check(label: str, condition: bool, failures: list) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        failures.append(label)


def tombstone_check(map_obj, insert_fn, lookup_fn, delete_fn, failures: list, label: str) -> None:
    keys = [f"{label}-key-{i}" for i in range(20)]
    for i, k in enumerate(keys):
        insert_fn(map_obj, k, i)
    # delete every other key, then confirm the REMAINING keys (whose probe
    # sequence may pass through a deleted slot) are still findable
    for i, k in enumerate(keys):
        if i % 2 == 0:
            delete_fn(map_obj, k)
    still_present = keys[1::2]
    all_found = all(lookup_fn(map_obj, k) == i for i, k in zip(range(1, len(keys), 2), still_present))
    check(f"{label}: keys past a tombstone are still findable after deletion", all_found, failures)

    deleted_raises = True
    for i, k in enumerate(keys):
        if i % 2 == 0:
            try:
                lookup_fn(map_obj, k)
                deleted_raises = False
            except KeyError:
                pass
    check(f"{label}: deleted keys raise KeyError on lookup", deleted_raises, failures)


def main() -> int:
    failures: list = []
    rng = random.Random(311)

    print("Building 50,000-key datasets...\n")
    keys = [f"key-{i}-{rng.randint(0, 1_000_000)}" for i in range(N_KEYS)]
    keys = list(dict.fromkeys(keys))  # de-duplicate just in case
    values = list(range(len(keys)))

    chained: ChainedHashMap = ChainedHashMap()
    linear: LinearProbingHashMap = LinearProbingHashMap()
    quadratic: QuadraticProbingHashMap = QuadraticProbingHashMap()

    for k, v in zip(keys, values):
        chained.insert(k, v)
        linear.insert(k, v)
        quadratic.insert(k, v)

    print("Verifying correctness of all 50,000 keys across all three maps...\n")
    chained_ok = all(chained.get(k) == v for k, v in zip(keys, values))
    linear_ok = all(linear.search(k) == v for k, v in zip(keys, values))
    quadratic_ok = all(quadratic.search(k) == v for k, v in zip(keys, values))

    check("ChainedHashMap retrieves all 50,000 keys correctly", chained_ok, failures)
    check("LinearProbingHashMap retrieves all 50,000 keys correctly", linear_ok, failures)
    check("QuadraticProbingHashMap retrieves all 50,000 keys correctly", quadratic_ok, failures)
    check("ChainedHashMap len() matches key count", len(chained) == len(keys), failures)
    check("LinearProbingHashMap len() matches key count", len(linear) == len(keys), failures)
    check("QuadraticProbingHashMap len() matches key count", len(quadratic) == len(keys), failures)

    for k in ["definitely-not-a-key-xyz", "another-absent-key"]:
        for name, m, lookup in [("ChainedHashMap", chained, chained.get), ("LinearProbingHashMap", linear, linear.search), ("QuadraticProbingHashMap", quadratic, quadratic.search)]:
            try:
                lookup(k)
                check(f"{name}.{'get' if name=='ChainedHashMap' else 'search'}('{k}') raises KeyError", False, failures)
            except KeyError:
                check(f"{name} lookup of an absent key raises KeyError", True, failures)

    print("\nRunning tombstone-deletion checks...\n")
    tombstone_check(ChainedHashMap(), lambda m, k, v: m.insert(k, v), lambda m, k: m.get(k), lambda m, k: m.delete(k), failures, "ChainedHashMap")
    tombstone_check(LinearProbingHashMap(), lambda m, k, v: m.insert(k, v), lambda m, k: m.search(k), lambda m, k: m.delete(k), failures, "LinearProbingHashMap")
    tombstone_check(QuadraticProbingHashMap(), lambda m, k, v: m.insert(k, v), lambda m, k: m.search(k), lambda m, k: m.delete(k), failures, "QuadraticProbingHashMap")

    if failures:
        print(f"\n{len(failures)} correctness check(s) failed. No token issued.")
        return 1

    print("\nMeasuring lookup performance and comparing against theory...\n")
    sample = rng.sample(list(zip(keys, values)), 5000)

    t_chained = timeit.timeit(lambda: [chained.get(k) for k, _ in sample], number=1)
    t_linear = timeit.timeit(lambda: [linear.search(k) for k, _ in sample], number=1)
    t_quadratic = timeit.timeit(lambda: [quadratic.search(k) for k, _ in sample], number=1)

    alpha_chained = len(chained) / len(chained._buckets) if hasattr(chained, "_buckets") else None
    alpha_linear = len(linear) / len(linear._keys) if hasattr(linear, "_keys") else None

    print(f"  ChainedHashMap:        {t_chained*1000:7.2f} ms / 5000 lookups", end="")
    if alpha_chained is not None:
        predicted = 1 + alpha_chained / 2
        print(f"   (alpha={alpha_chained:.2f}, theoretical successful-search comparisons ~= {predicted:.2f})")
    else:
        print()

    print(f"  LinearProbingHashMap:  {t_linear*1000:7.2f} ms / 5000 lookups", end="")
    if alpha_linear is not None and alpha_linear < 1:
        predicted = 0.5 * (1 + 1 / (1 - alpha_linear))
        print(f"   (alpha={alpha_linear:.2f}, theoretical successful-search probes ~= {predicted:.2f})")
    else:
        print()

    print(f"  QuadraticProbingHashMap: {t_quadratic*1000:7.2f} ms / 5000 lookups (no simple closed form -- compare qualitatively to linear probing)\n")

    fastest = min(t_chained, t_linear, t_quadratic)
    slowest = max(t_chained, t_linear, t_quadratic)
    ratio = slowest / fastest if fastest > 0 else math.inf
    check("no structure is more than 10x slower per-lookup than the fastest (rules out an accidental O(n) scan)", ratio < 10, failures)

    if failures:
        print(f"\n{len(failures)} check(s) failed. No token issued.")
        return 1

    print_success_banner(ASSIGNMENT_ID)
    return 0


if __name__ == "__main__":
    sys.exit(main())
