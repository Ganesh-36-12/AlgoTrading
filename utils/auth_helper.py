import time
import random

RATE_LIMIT_HINTS = ("exceeding access rate", "rate", "429", "too many requests", "access denied")

def is_rate_limit_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(h in msg for h in RATE_LIMIT_HINTS)

def auth_with_backoff(trader, tries=5, base_delay=1.0, on_status=None):
    for attempt in range(tries):
        try:
            trader.authenticate()
            return trader
        except Exception as e:
            if is_rate_limit_error(e) and attempt < tries - 1:
                # exponential backoff + jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                if callable(on_status):
                    on_status(f"Rate limit for {trader.CLIENT}. Retry in {delay:.1f}s (attempt {attempt+1}/{tries})")
                time.sleep(delay)
                continue
            raise

def authenticate_all_sequential(master_obj, child_objs, on_status=None, on_result=None, delay_between=2.0):
    successes, failures = [], {}

    all_traders = [master_obj, *child_objs]
    if callable(on_status):
        on_status(f"available trader: {type(child_objs)}")
    for idx, t in enumerate(all_traders):
        try:
            if callable(on_status):
                on_status(f"Authenticating {t.CLIENT} ({idx+1}/{len(all_traders)})...")
            auth_with_backoff(t, tries=5, base_delay=1.0, on_status=on_status)
            successes.append(t)
            if callable(on_result):
                on_result(t, True, None)
            time.sleep(delay_between)  # gentle spacing prevents bursts
        except Exception as e:
            failures[t] = e
            if callable(on_result):
                on_result(t, False, e)

    if callable(on_status):
        on_status("All accounts authenticated (sequential)")
    return successes, failures

