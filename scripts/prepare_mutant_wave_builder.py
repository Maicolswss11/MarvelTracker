#!/usr/bin/env python3
from pathlib import Path

path = Path("scripts/build_mutant_street_wave.py")
text = path.read_text(encoding="utf-8")

source_old = '    loaded, source_errors = street.load_config_sources(config, workers)\n    filtered_roles, filtered_role_errors = filtered_source_roles(config, loaded, workers)\n'
source_new = '''    # Keep source-index traffic conservative: ComicsBox throttles large bursts.
    source_workers = min(workers, 8)
    loaded, source_errors = street.load_config_sources(config, source_workers)
    retry_delays = (5, 15, 30, 60)
    for retry, delay in enumerate(retry_delays, 1):
        if not source_errors:
            break
        failed_codes = ", ".join(sorted(source_errors))
        log(f"Retry sorgenti ComicsBox {retry}/{len(retry_delays)} tra {delay}s: {failed_codes}")
        __import__("time").sleep(delay)
        for code in list(source_errors):
            try:
                loaded[code] = legacy.load_foreign_series(code)
                source_errors.pop(code, None)
            except Exception as error:
                source_errors[code] = str(error)
    if source_errors:
        details = "; ".join(f"{code}: {error}" for code, error in sorted(source_errors.items()))
        raise RuntimeError(f"ComicsBox source load failed after retries: {details}")
    log(f"Sorgenti ComicsBox complete: {len(loaded)}/77")
    filtered_roles, filtered_role_errors = filtered_source_roles(config, loaded, min(workers, 16))
'''
if source_old not in text:
    raise SystemExit("builder source-load anchor not found")
text = text.replace(source_old, source_new, 1)

filtered_old = '''            if index % 100 == 0 or index == len(futures):
                log(f"Storie USA di squadra filtrate: {index}/{len(futures)}")
    return result, errors
'''
filtered_new = '''            if index % 100 == 0 or index == len(futures):
                log(f"Storie USA di squadra filtrate: {index}/{len(futures)}")

    retry_delays = (3, 10, 30, 60)
    for retry, delay in enumerate(retry_delays, 1):
        if not errors:
            break
        failed_codes = sorted(errors)
        log(
            f"Retry storie team {retry}/{len(retry_delays)} tra {delay}s: "
            + ", ".join(failed_codes)
        )
        __import__("time").sleep(delay)
        for code in failed_codes:
            try:
                key, paths = inspect(code)
                result[key] = paths
                errors.pop(code, None)
            except Exception as error:
                errors[code] = str(error)
    if errors:
        details = "; ".join(f"{code}: {error}" for code, error in sorted(errors.items()))
        raise RuntimeError(f"ComicsBox filtered team scan failed after retries: {details}")
    return result, errors
'''
if filtered_old not in text:
    raise SystemExit("filtered-role retry anchor not found")
text = text.replace(filtered_old, filtered_new, 1)

shared_old = '''    role_map, role_errors = wave1.scan_content_roles(reuse_contents, config, workers)

    chapters_by_path: dict[str, list[dict[str, Any]]] = {}
'''
shared_new = '''    role_map, role_errors = wave1.scan_content_roles(reuse_contents, config, workers)
    aliases_by_path = {path["id"]: path["aliases"] for path in config["paths"]}
    retry_delays = (3, 10, 30, 60)
    for retry, delay in enumerate(retry_delays, 1):
        if not role_errors:
            break
        failed_codes = sorted(role_errors)
        log(
            f"Retry storie condivise {retry}/{len(retry_delays)} tra {delay}s: "
            + ", ".join(failed_codes)
        )
        __import__("time").sleep(delay)
        for code in failed_codes:
            try:
                source = legacy.fetch_text(f"https://www.comicsbox.it/albo/{code}")
                date_label, date_key = wave1.source_date(source)
                protagonists = [
                    path_id
                    for path_id, aliases in aliases_by_path.items()
                    if wave1.credited_as_protagonist(source, aliases)
                ]
                role_map[code] = {
                    "protagonistPaths": protagonists,
                    "date": date_label,
                    "dateKey": list(date_key),
                }
                role_errors.pop(code, None)
            except Exception as error:
                role_errors[code] = str(error)
    if role_errors:
        details = "; ".join(f"{code}: {error}" for code, error in sorted(role_errors.items()))
        raise RuntimeError(f"ComicsBox shared story scan failed after retries: {details}")

    chapters_by_path: dict[str, list[dict[str, Any]]] = {}
'''
if shared_old not in text:
    raise SystemExit("shared-role retry anchor not found")
text = text.replace(shared_old, shared_new, 1)

path.write_text(text, encoding="utf-8")
print("Mutant/street builder hardened for ComicsBox retries.")
