#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mihomo-adblock-rules: High-performance AdBlock ruleset builder and optimizer.
Combines and prunes redundant subdomains for Server (full) and Client (lite) profiles.
"""

import os
import sys
import argparse
import datetime
import hashlib
import ssl
import subprocess
import urllib.request

# Disable SSL verification for maximum compatibility across environments
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

PROBE_DOMAIN = "7h15.ru1353t.1s.m4d3.by.5ukk4w.skk.moe"

SERVER_SOURCES = [
    {
        "name": "Loyalsoldier Reject",
        "url": "https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/reject.txt",
        "format": "yaml_list"
    },
    {
        "name": "Sukka Reject Base",
        "url": "https://ruleset.skk.moe/Clash/domainset/reject.txt",
        "format": "domainset"
    },
    {
        "name": "Sukka Reject Extra",
        "url": "https://ruleset.skk.moe/Clash/domainset/reject_extra.txt",
        "format": "domainset"
    }
]

CLIENT_SOURCES = [
    {
        "name": "MetaCubeX category-ads-all",
        "url": "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ads-all.list",
        "format": "domainset"
    },
    {
        "name": "Sukka Reject Non-IP",
        "url": "https://ruleset.skk.moe/Clash/non_ip/reject.txt",
        "format": "domainset"
    },
    {
        "name": "Sukka Reject No-Drop",
        "url": "https://ruleset.skk.moe/Clash/non_ip/reject-no-drop.txt",
        "format": "domainset"
    },
    {
        "name": "217heidai AdBlock Lite",
        "url": "https://cdn.jsdelivr.net/gh/217heidai/adblockfilters/rules/adblockmihomolite.yaml",
        "format": "yaml_list"
    },
    {
        "name": "AWAvenue Ads Classical",
        "url": "https://cdn.jsdelivr.net/gh/TG-Twilight/AWAvenue-Ads-Rule@main/Filters/AWAvenue-Ads-Rule-Clash-Classical.yaml",
        "format": "yaml_list"
    }
]


def fetch_url_content(url, local_cache_dir=None):
    # Unique cache key based on URL hash to prevent collisions between identical basenames
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    base_name = os.path.basename(url.split("?")[0])
    cache_name = f"{url_hash}_{base_name}"

    if local_cache_dir:
        cpath = os.path.join(local_cache_dir, cache_name)
        if os.path.exists(cpath) and os.path.getsize(cpath) > 0:
            print(f"  [Cache] Using local cache for {base_name} ({cache_name})")
            with open(cpath, "rb") as f:
                return f.read()

    print(f"  [Download] Fetching {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MihomoRulesBuilder/1.0)"})
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as resp:
        content = resp.read()

    if local_cache_dir:
        os.makedirs(local_cache_dir, exist_ok=True)
        cpath = os.path.join(local_cache_dir, cache_name)
        with open(cpath, "wb") as f:
            f.write(content)

    return content


def parse_rules_from_content(content_bytes):
    """
    Parses various rule formats into a pair of sets: (suffix_domains, exact_domains)
    """
    text = content_bytes.decode("utf-8", errors="ignore")
    suffix_domains = set()
    exact_domains = set()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if PROBE_DOMAIN in line:
            continue
        if line == "payload:":
            continue

        # Strip yaml list indicator
        if line.startswith("-"):
            line = line[1:].strip().strip("'\"")

        if not line:
            continue

        # Handle classical formats (e.g. DOMAIN-SUFFIX,example.com or DOMAIN,example.com)
        if line.startswith("DOMAIN-SUFFIX,"):
            parts = line.split(",")
            if len(parts) >= 2:
                domain = parts[1].strip().lower().lstrip("+.")
                if domain:
                    suffix_domains.add(domain)
            continue
        elif line.startswith("DOMAIN,"):
            parts = line.split(",")
            if len(parts) >= 2:
                domain = parts[1].strip().lower().lstrip("+.")
                if domain:
                    exact_domains.add(domain)
            continue
        elif line.startswith("DOMAIN-KEYWORD,") or line.startswith("DOMAIN-REGEX,") or line.startswith("IP-CIDR"):
            # Domain-specific strategy doesn't handle IP or regex
            continue

        # Handle +., ., or plain domain
        if line.startswith("+."):
            clean = line[2:].strip().lower()
            if clean:
                suffix_domains.add(clean)
        elif line.startswith("."):
            clean = line[1:].strip().lower()
            if clean:
                suffix_domains.add(clean)
        else:
            clean = line.strip().lower()
            if clean:
                exact_domains.add(clean)

    return suffix_domains, exact_domains


class DomainPruner:
    """
    Efficient reverse-domain Trie to detect and prune redundant subdomains.
    Example: If +.example.com exists, then +.sub.example.com and sub.example.com are redundant.
    """
    def __init__(self):
        self.root = {}

    def insert_suffix(self, domain):
        parts = domain.split(".")[::-1]
        node = self.root
        for part in parts:
            if part not in node:
                node[part] = {}
            node = node[part]
        node["__suffix__"] = True

    def insert_exact(self, domain):
        parts = domain.split(".")[::-1]
        node = self.root
        for part in parts:
            if part not in node:
                node[part] = {}
            node = node[part]
        node["__exact__"] = True

    def is_redundant_suffix(self, domain):
        """
        Check if any strictly higher-level suffix covers this domain.
        """
        parts = domain.split(".")[::-1]
        node = self.root
        # Must check strictly ancestors
        for i in range(len(parts) - 1):
            part = parts[i]
            if part not in node:
                return False
            node = node[part]
            if node.get("__suffix__"):
                return True
        return False

    def is_redundant_exact(self, domain):
        """
        Check if any ancestor suffix (or same-level suffix) covers this exact domain.
        """
        parts = domain.split(".")[::-1]
        node = self.root
        for part in parts:
            if part not in node:
                return False
            node = node[part]
            if node.get("__suffix__"):
                return True
        return False


def prune_and_sort_rules(all_suffixes, all_exacts):
    """
    Prunes redundant rules and outputs sorted canonical representations.
    Returns: list of formatted string rules (e.g. "+.example.com", "exact.com")
    """
    # If a domain is present in both suffix and exact, suffix takes precedence
    all_exacts = all_exacts - all_suffixes

    # Build suffix tree
    pruner = DomainPruner()
    for s in all_suffixes:
        pruner.insert_suffix(s)

    # 1. Prune redundant suffixes
    clean_suffixes = set()
    for s in all_suffixes:
        if not pruner.is_redundant_suffix(s):
            clean_suffixes.add(s)

    # Rebuild pruner with only clean suffixes for exact matching
    pruner_clean = DomainPruner()
    for s in clean_suffixes:
        pruner_clean.insert_suffix(s)

    # 2. Prune redundant exacts
    clean_exacts = set()
    for e in all_exacts:
        if not pruner_clean.is_redundant_exact(e):
            clean_exacts.add(e)

    # Format into canonical strings
    results = []
    for s in clean_suffixes:
        results.append(f"+.{s}")
    for e in clean_exacts:
        results.append(e)

    # Lexicographical sort (sorting by domain name without prefix for consistency)
    def sort_key(rule):
        d = rule[2:] if rule.startswith("+.") else rule
        return (d, rule)

    results.sort(key=sort_key)
    return results, len(all_suffixes) + len(all_exacts), len(results)


def build_profile(sources, profile_name, output_dir, local_cache_dir=None):
    print(f"\n==================== Building Profile: {profile_name} ====================")
    total_raw_suffixes = set()
    total_raw_exacts = set()

    for src in sources:
        print(f"Processing source: {src['name']} ...")
        try:
            content = fetch_url_content(src["url"], local_cache_dir=local_cache_dir)
            s_set, e_set = parse_rules_from_content(content)
            print(f"  -> Extracted {len(s_set)} wildcard suffixes, {len(e_set)} exact domains")
            total_raw_suffixes.update(s_set)
            total_raw_exacts.update(e_set)
        except Exception as ex:
            print(f"  [ERROR] Failed to fetch {src['name']}: {ex}")
            raise ex

    print(f"\nTotal raw unique entries before pruning: {len(total_raw_suffixes)} suffixes, {len(total_raw_exacts)} exacts")
    clean_rules, raw_count, pruned_count = prune_and_sort_rules(total_raw_suffixes, total_raw_exacts)
    pruned_removed = raw_count - pruned_count
    print(f"Pruning complete: {raw_count} -> {pruned_count} rules (removed {pruned_removed} redundant subdomains, saved {pruned_removed/raw_count*100:.2f}%)")

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Output .list / .txt file
    list_path = os.path.join(output_dir, f"{profile_name}.list")
    txt_path = os.path.join(output_dir, f"{profile_name}.txt")
    header_comment = (
        f"# Title: Mihomo AdBlock Rules - {profile_name.capitalize()}\n"
        f"# Total Rules: {pruned_count}\n"
        f"# Updated: {now_utc}\n"
        f"# Homepage: https://github.com/metacubex/mihomo\n"
        f"# License: AGPL-3.0 / MIT\n"
        f"#\n"
    )

    with open(list_path, "w", encoding="utf-8") as f:
        f.write(header_comment)
        for r in clean_rules:
            f.write(f"{r}\n")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(header_comment)
        for r in clean_rules:
            f.write(f"{r}\n")

    # 2. Output .yaml file
    yaml_path = os.path.join(output_dir, f"{profile_name}.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(header_comment)
        f.write("payload:\n")
        for r in clean_rules:
            f.write(f"  - '{r}'\n")

    # 3. Generate SHA256 checksums
    for p in [list_path, txt_path, yaml_path]:
        with open(p, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        with open(f"{p}.sha256sum", "w", encoding="utf-8") as f:
            f.write(f"{digest}  {os.path.basename(p)}\n")

    # 4. Optional: compile to .mrs binary format if Go converter is available
    converter_dir = os.path.join(os.path.dirname(__file__), "mrs_converter")
    mrs_path = os.path.join(output_dir, f"{profile_name}.mrs")
    if os.path.exists(os.path.join(converter_dir, "main.go")):
        cmd = ["go", "run", ".", "-in", yaml_path, "-out", mrs_path]
        try:
            res = subprocess.run(cmd, cwd=converter_dir, capture_output=True, text=True, check=True)
            if os.path.exists(mrs_path):
                with open(mrs_path, "rb") as f:
                    digest = hashlib.sha256(f.read()).hexdigest()
                with open(f"{mrs_path}.sha256sum", "w", encoding="utf-8") as f:
                    f.write(f"{digest}  {os.path.basename(mrs_path)}\n")
                print(f"  - {mrs_path} ({os.path.getsize(mrs_path):,} bytes)")
        except Exception as e:
            print(f"  [Notice] Could not auto-compile mrs: {e}")

    print(f"Generated artifacts for {profile_name}:")
    print(f"  - {list_path} ({os.path.getsize(list_path):,} bytes)")
    print(f"  - {txt_path}")
    print(f"  - {yaml_path} ({os.path.getsize(yaml_path):,} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Build and optimize mihomo adblock rulesets.")
    parser.add_argument("--profile", choices=["all", "server", "client"], default="all", help="Profile to build")
    parser.add_argument("--output", default="publish", help="Output directory for generated rules")
    parser.add_argument("--cache", default="cache", help="Cache directory for downloaded sources")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    os.makedirs(args.cache, exist_ok=True)

    start_time = datetime.datetime.now()

    if args.profile in ["all", "server"]:
        build_profile(SERVER_SOURCES, "reject-server", args.output, local_cache_dir=args.cache)

    if args.profile in ["all", "client"]:
        build_profile(CLIENT_SOURCES, "reject-client", args.output, local_cache_dir=args.cache)

    elapsed = (datetime.datetime.now() - start_time).total_seconds()
    print(f"\nAll builds completed successfully in {elapsed:.2f} seconds.")


if __name__ == "__main__":
    main()
