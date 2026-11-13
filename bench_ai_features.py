#!/usr/bin/env python3
"""无头实战验证：跑真实对战，测量三个 AI 新特性的实际表现，并做 A/B 对比。

三个特性
--------
1. 多线补兵 —— 同时有几座生产建筑在造兵、订单怎么分布
2. 经济调度 —— 采集工人分布在几个食物源上、最集中的那个占多少
3. TC 数量管理 —— 主基地数量随时间的变化

A/B
---
--ab 模式下，同一个 AI 类型跑两局：一局正常，一局把多线补兵关掉
（multi_queue_limit 强制返回 0），用来量出多线补兵到底带来多少兵。

用法
----
  python bench_ai_features.py --ai beginner expert --game-minutes 15
  python bench_ai_features.py --ai expert --ab --game-minutes 20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
DEFAULT_MAP = _HERE / "res" / "multi" / "cw1.txt"


def _parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--map", type=Path, default=DEFAULT_MAP)
    p.add_argument("--game-minutes", type=float, default=8.0)
    p.add_argument("--wall-seconds", type=float, default=0)
    p.add_argument("--nb-ai", type=int, default=6)
    p.add_argument("--ai", nargs="+", default=["beginner", "expert"])
    p.add_argument("--mods", default="aoe2")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--ab", action="store_true",
                   help="also run each AI type with the multi-queue disabled")
    p.add_argument("--report", type=Path, default=_HERE / "bench_ai_features_report.txt")
    p.add_argument("--json", type=Path, default=_HERE / "bench_ai_features_report.json")
    return p.parse_args(argv)


def _soldier_count(player):
    """How many combat units the player owns."""
    from soundrts.worldunit.worldsoldier import Soldier
    n = 0
    for u in getattr(player, "units", ()) or ():
        if isinstance(u, Soldier):
            n += 1
    return n


def _base_count(player):
    try:
        bases = player._main_base_type_names()
        if not bases:
            return 0
        return player.future_nb(list(bases))
    except Exception:
        return 0


class Probes:
    """Monkeypatch the Computer so we can count what really happened."""

    def __init__(self):
        self.multi_queue_calls = 0
        self.multi_queue_rounds = 0
        self.multi_queue_orders = 0
        self.hosts_used = Counter()
        self.hosts_seen = set()
        self.gather_picks = Counter()
        self.gather_workers = set()
        self.mq_wanted = []
        self.mq_plan_lines = set()
        self._get_calls = 0
        self._busy_snapshot = []
        self.mq_stages = {
            "calls": 0, "no_tier": 0, "one_host": 0, "no_idle": 0,
            "no_wanted": 0, "no_budget": 0, "no_capable_host": 0,
            "no_cls": 0, "no_resources": 0, "food_protected": 0,
            "reached_train": 0,
            "host_counts": [], "idle_counts": [], "budget_counts": [],
            "capable": [],
        }
        self._patched = []

    def install(self):
        from soundrts.worldplayercomputer import Computer
        from soundrts.definitions import rules
        from soundrts import world_ai_economy as econ

        self._orig_mq = Computer._maintain_multi_queue_production
        self._orig_train = Computer._train_on_extra_queue
        self._orig_gather = Computer._choose_gather_target_compute
        self._orig_hosts = Computer._owned_production_hosts
        self._orig_wanted = Computer._multi_queue_wanted_army_types

        probes = self

        def mq(self):
            probes.multi_queue_calls += 1
            wanted = probes._orig_wanted(self)
            if wanted:
                probes.mq_wanted.extend(wanted)
                probes.mq_plan_lines.add(str(self._plan[self._line_nb]))
            d = probes.mq_stages
            d["calls"] += 1
            if not econ.should_open_extra_queue(getattr(self, "AI_type", None)):
                d["no_tier"] += 1
                return probes._orig_mq(self)
            hosts = probes._orig_hosts(self)
            d["host_counts"].append(len(hosts))
            if len(hosts) < 2:
                d["one_host"] += 1
                return probes._orig_mq(self)
            idle = [h for h in hosts if not econ.production_queue_depth(h)]
            d["idle_counts"].append(len(idle))
            if not idle:
                d["no_idle"] += 1
                return probes._orig_mq(self)
            if not wanted:
                d["no_wanted"] += 1
                return probes._orig_mq(self)
            limit = econ.multi_queue_limit(getattr(self, "AI_type", None))
            running = len(hosts) - len(idle)
            budget = min(limit - running, len(idle))
            d["budget_counts"].append(budget)
            if budget <= 0:
                d["no_budget"] += 1
                return probes._orig_mq(self)
            for type_name, missing in wanted:
                capable = self._hosts_that_can_train(type_name, idle)
                d["capable"].append((type_name, len(capable)))
                if not capable:
                    d["no_capable_host"] += 1
                    continue
                cls = rules.unit_class(type_name)
                if cls is None:
                    d["no_cls"] += 1
                    continue
                cost = tuple(getattr(cls, "cost", None) or ())
                if self.missing_resources(cost):
                    d["no_resources"] += 1
                    continue
                if not self._extra_queue_may_spend_food(cost):
                    d["food_protected"] += 1
                    continue
                d["reached_train"] += 1
            res = probes._orig_mq(self)
            if res:
                probes.multi_queue_rounds += 1
            return res

        def train(self, type_name, host, cost):
            ok = probes._orig_train(self, type_name, host, cost)
            if ok:
                probes.multi_queue_orders += 1
                probes.hosts_used[getattr(host, "id", None)] += 1
            return ok

        def gather(self, worker, origin, resource_indices=None):
            target = probes._orig_gather(self, worker, origin, resource_indices)
            if target is not None:
                wid = getattr(worker, "id", None)
                tid = getattr(target, "id", None)
                if wid is not None and tid is not None:
                    probes.gather_picks[wid] = tid
                    probes.gather_workers.add(wid)
            return target

        def hosts(self):
            hs = probes._orig_hosts(self)
            for h in hs:
                probes.hosts_seen.add(getattr(h, "id", None))
            return hs

        # --- how many buildings carry a train order at the same time? ---
        def _busy_hosts(self):
            n = 0
            for h in probes._orig_hosts(self):
                if econ.production_queue_depth(h):
                    n += 1
            return n

        def _get(self, nb, types):
            probes._get_calls += 1
            probes._busy_snapshot.append(_busy_hosts(self))
            return probes._orig_get(self, nb, types)

        self._orig_get = Computer._get

        Computer._maintain_multi_queue_production = mq
        Computer._train_on_extra_queue = train
        Computer._choose_gather_target_compute = gather
        Computer._owned_production_hosts = hosts
        Computer._get = _get
        self._patched = [
            (Computer, "_maintain_multi_queue_production", self._orig_mq),
            (Computer, "_train_on_extra_queue", self._orig_train),
            (Computer, "_choose_gather_target_compute", self._orig_gather),
            (Computer, "_owned_production_hosts", self._orig_hosts),
            (Computer, "_get", self._orig_get),
        ]

    def remove(self):
        for cls, name, orig in self._patched:
            setattr(cls, name, orig)
        self._patched = []


class _NoMultiQueue:
    """Context manager: force the multi-queue limit to 0 (the A/B control)."""

    def __enter__(self):
        from soundrts import world_ai_economy as econ
        self._orig = econ.multi_queue_limit
        econ.multi_queue_limit = lambda ai_type: 0
        # worldplayercomputer imported the module, not the function, so
        # patching the module attribute is enough.
        return self

    def __exit__(self, *exc):
        from soundrts import world_ai_economy as econ
        econ.multi_queue_limit = self._orig
        return False


class _ExpansionProbe:
    """Count why _maintain_expansions did not open a new base."""

    def __init__(self):
        self.calls = 0
        self.reasons = Counter()
        self.pressures = []
        self._patched = []

    def install(self):
        from soundrts.worldplayercomputer import Computer
        from soundrts import world_ai_economy as econ

        self._orig = Computer._maintain_expansions
        probes = self

        def exp(self):
            probes.calls += 1
            bases = self._main_base_type_names()
            if not bases:
                probes.reasons["no_base_type"] += 1
                return probes._orig(self)
            target = self._target_townhalls
            if target <= 0:
                target = self._automatic_base_target()
                probes.pressures.append(
                    (round(getattr(self, "population", 0), 1),
                     round(getattr(self, "used_population", 0), 1),
                     target,
                     tuple(round(r, 0) for r in (getattr(self, "resources", None) or ())[:3])))
                if target <= 0:
                    probes.reasons["auto_target_0"] += 1
                    return probes._orig(self)
            if self.future_nb(list(bases)) >= target:
                probes.reasons["already_enough"] += 1
                return probes._orig(self)
            cls = rules_unit_class(bases[0])
            if cls is None:
                probes.reasons["no_cls"] += 1
                return probes._orig(self)
            if self.missing_resources(cls.cost):
                probes.reasons["no_resources"] += 1
                return probes._orig(self)
            if not econ.base_is_worth_expanding(rules, bases[0]):
                probes.reasons["not_worth"] += 1
                return probes._orig(self)
            if self._plan_expensive_wood_reserve(ignore_age_defer=True):
                probes.reasons["wood_reserve"] += 1
                return probes._orig(self)
            probes.reasons["built"] += 1
            return probes._orig(self)

        Computer._maintain_expansions = exp
        self._patched = [(Computer, "_maintain_expansions", self._orig)]

    def remove(self):
        for cls, name, orig in self._patched:
            setattr(cls, name, orig)
        self._patched = []


def _run_one(ai_type, args, disable_multi_queue=False):
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DummyClient

    if args.mods:
        res.set_mods(args.mods)
    res.load_rules_and_ai()

    probes = Probes()
    probes.install()
    exp_probe = _ExpansionProbe()
    exp_probe.install()
    ctx = _NoMultiQueue() if disable_multi_queue else None
    try:
        if ctx:
            ctx.__enter__()
        text = args.map.read_text(encoding="utf-8")
        world = World([], args.seed)
        world._parse_map(text)
        from soundrts.lib.nofloat import PRECISION
        world.square_width = int(world.square_width * PRECISION)
        world._build_map()
        clients = []
        for i in range(args.nb_ai):
            c = DummyClient(ai_type)
            c.faction = rules.factions[0]
            c.alliance = "1" if i % 2 == 0 else "2"
            clients.append(c)
        world.populate_map(clients, random_starts=False)

        game_limit_ms = int(args.game_minutes * 60 * 1000)
        wall0 = time.perf_counter()
        next_sample = 0
        ticks = 0
        army_series = []
        base_series = []
        while world.time < game_limit_ms:
            world.update()
            ticks += 1
            if world.time >= next_sample:
                comps = [pl for pl in world.players
                         if getattr(pl, "is_computer_player", False)]
                armies = [_soldier_count(pl) for pl in comps]
                bases = [_base_count(pl) for pl in comps]
                minute = round(world.time / 60000.0, 2)
                army_series.append((minute, sum(armies), max(armies) if armies else 0))
                base_series.append((minute, max(bases) if bases else 0,
                                    min(bases) if bases else 0))
                next_sample = world.time + 60000
            if args.wall_seconds and (time.perf_counter() - wall0) >= args.wall_seconds:
                break
    finally:
        if ctx:
            ctx.__exit__(None, None, None)
        exp_probe.remove()
        probes.remove()

    picks = probes.gather_picks
    target_counts = Counter(picks.values())
    workers = len(probes.gather_workers)

    final_armies = []
    final_bases = []
    for pl in world.players:
        if not getattr(pl, "is_computer_player", False):
            continue
        final_armies.append(_soldier_count(pl))
        final_bases.append(_base_count(pl))

    host_counts = probes.hosts_used
    stages = probes.mq_stages
    return {
        "ai_type": ai_type,
        "multi_queue_disabled": disable_multi_queue,
        "ticks": ticks,
        "game_minutes": round(world.time / 60000.0, 2),
        # multi-queue
        "production_hosts_seen": len(probes.hosts_seen),
        "mq_calls": probes.multi_queue_calls,
        "mq_rounds": probes.multi_queue_rounds,
        "mq_orders": probes.multi_queue_orders,
        "mq_hosts_used": len(host_counts),
        "mq_per_host": host_counts.most_common(8),
        "mq_wanted": Counter(probes.mq_wanted).most_common(5),
        "mq_plan_lines": sorted(probes.mq_plan_lines)[:6],
        "mq_stages": {k: (v if not isinstance(v, list) else (
            {"max": max(x[1] for x in v) if v else 0,
             "avg": round(sum(x[1] for x in v) / len(v), 2) if v else 0,
             "n": len(v)}
            if v and isinstance(v[0], tuple) else
            {"max": max(v) if v else 0,
             "avg": round(sum(v) / len(v), 2) if v else 0, "n": len(v)}))
            for k, v in stages.items()},
        # economic scheduling
        "gather_workers": workers,
        "gather_distinct_targets": len(target_counts),
        "gather_max_share": round(max(target_counts.values()) / workers, 3) if workers else 0.0,
        "gather_top_targets": target_counts.most_common(5),
        # base management
        "final_bases": final_bases,
        "max_bases": max(final_bases) if final_bases else 0,
        "bases_over_time": base_series,
        # army
        "final_armies": final_armies,
        "max_army": max(final_armies) if final_armies else 0,
        "total_army": sum(final_armies),
        "army_over_time": army_series,
        # how parallel the regular path already is
        "get_calls": probes._get_calls,
        "busy_hosts_histogram": dict(Counter(probes._busy_snapshot).most_common()),
        # expansion
        "exp_calls": exp_probe.calls,
        "exp_reasons": dict(exp_probe.reasons),
        "exp_pressure_sample": exp_probe.pressures[-6:],
    }


def _fmt(r):
    L = []
    L.append("")
    L.append(f"### AI = {r['ai_type']}"
             + ("   [MULTI-QUEUE DISABLED (control)]" if r["multi_queue_disabled"] else "")
             + f"   ({r['game_minutes']} game-minutes, {r['ticks']} ticks)")
    L.append("  MULTI-QUEUE (多线补兵)")
    L.append(f"    production hosts seen       : {r['production_hosts_seen']}")
    L.append(f"    extra-queue orders placed   : {r['mq_orders']}")
    L.append(f"    distinct hosts used         : {r['mq_hosts_used']}")
    L.append(f"    orders per host             : {r['mq_per_host']}")
    L.append(f"    bail-out counters           : "
             + ", ".join(f"{k}={v}" for k, v in r["mq_stages"].items()
                         if isinstance(v, int)))
    L.append("  ECONOMIC SCHEDULING (经济调度)")
    L.append(f"    workers that picked a target: {r['gather_workers']}")
    L.append(f"    distinct gather targets     : {r['gather_distinct_targets']}")
    L.append(f"    biggest target share        : {r['gather_max_share']}")
    L.append(f"    top targets                 : {r['gather_top_targets']}")
    L.append("  BASE MANAGEMENT (TC 数量管理)")
    L.append(f"    final bases per AI          : {r['final_bases']}")
    L.append(f"    max bases                   : {r['max_bases']}")
    L.append(f"    expansion calls             : {r['exp_calls']}")
    L.append(f"    expansion bail-outs         : {r['exp_reasons']}")
    L.append(f"    pop pressure sample (pop,cap,target): {r['exp_pressure_sample']}")
    L.append("  ARMY")
    L.append(f"    final armies per AI         : {r['final_armies']}")
    L.append(f"    max army / total army       : {r['max_army']} / {r['total_army']}")
    L.append(f"    army over time (min,sum,max): {r['army_over_time']}")
    L.append(f"    bases over time (min,max)   : {r['bases_over_time']}")
    L.append("  PARALLELISM OF THE REGULAR PATH")
    L.append(f"    _get() calls                : {r['get_calls']}")
    L.append(f"    busy hosts histogram        : {r['busy_hosts_histogram']}")
    return "\n".join(L)


def main(argv=None):
    args = _parse_args(argv)
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    sys.path.insert(0, str(_HERE))
    # soundrts/options.py runs optparse.parse_args() on the real sys.argv at
    # import time, so it would eat our own flags and exit.  Parse ours first,
    # then hide argv from the engine.
    _argv0 = sys.argv[0] if sys.argv else "bench_ai_features.py"
    sys.argv = [_argv0]

    results = []
    for ai_type in args.ai:
        print(f"[bench_ai_features] running {ai_type} ...", flush=True)
        r = _run_one(ai_type, args)
        results.append(r)
        print(f"[bench_ai_features] {ai_type}: mq_orders={r['mq_orders']} "
              f"hosts={r['mq_hosts_used']} targets={r['gather_distinct_targets']} "
              f"max_share={r['gather_max_share']} bases={r['max_bases']} "
              f"army={r['max_army']}", flush=True)
        if args.ab:
            print(f"[bench_ai_features] running {ai_type} (control, no "
                  f"multi-queue) ...", flush=True)
            rc = _run_one(ai_type, args, disable_multi_queue=True)
            results.append(rc)
            print(f"[bench_ai_features] {ai_type} control: "
                  f"army={rc['max_army']} targets={rc['gather_distinct_targets']} "
                  f"max_share={rc['gather_max_share']} bases={rc['max_bases']}",
                  flush=True)

    parts = ["=" * 78, "AI FEATURES HEADLESS VERIFICATION", "=" * 78]
    for r in results:
        parts.append(_fmt(r))

    # A/B summary
    if args.ab:
        parts.append("")
        parts.append("=" * 78)
        parts.append("A/B SUMMARY (multi-queue ON vs OFF, same seed)")
        parts.append("=" * 78)
        for ai_type in args.ai:
            on = [r for r in results if r["ai_type"] == ai_type
                  and not r["multi_queue_disabled"]]
            off = [r for r in results if r["ai_type"] == ai_type
                   and r["multi_queue_disabled"]]
            if not on or not off:
                continue
            on, off = on[0], off[0]
            parts.append(f"  {ai_type}:")
            parts.append(f"    extra-queue orders : ON={on['mq_orders']:4d}  OFF={off['mq_orders']}")
            parts.append(f"    max army size      : ON={on['max_army']:4d}  OFF={off['max_army']}")
            parts.append(f"    total army         : ON={on['total_army']:4d}  OFF={off['total_army']}")
            delta = on["total_army"] - off["total_army"]
            pct = (100.0 * delta / off["total_army"]) if off["total_army"] else 0.0
            parts.append(f"    delta              : {delta:+d} ({pct:+.1f} %)")

    text = "\n".join(parts)
    print("")
    print(text)
    args.report.write_text(text, encoding="utf-8")
    args.json.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {args.report} and {args.json}")


if __name__ == "__main__":
    main()
