# import threading

# def authenticate_all(master_obj,child_objs,on_status=None, on_result=None):
#     threads = []
#     def safe_auth(trader):
#         try:   
#             trader.authenticate()  # blocking I/O (network), fine in a thread
#             if callable(on_result):
#                 on_result(trader, True, None)
#         except Exception as e:
#             if callable(on_status):
#                 on_status(f"AUTH ERROR {trader.name}: {e}")
#             if callable(on_result):
#                 on_result(trader, False, e)
                
#     t_master = threading.Thread(target=safe_auth,args=(master_obj,))
    
#     threads.append(t_master)
#     t_master.start()
#     for child in child_objs:
#         t = threading.Thread(target=safe_auth,args=(child,))
#         threads.append(t)
#         t.start()
#     for t in threads:
#         t.join()
#     # print("All accounts authenticated")
    
    
#     if callable(on_status):
#         on_status("All accounts authenticated and done")


from concurrent.futures import ThreadPoolExecutor, as_completed

def authenticate_all(master_obj, child_objs, on_status=None, on_result=None, max_workers=8):
    """
    Authenticate master and children concurrently.
    Returns:
        successes: list of trader objects that authenticated successfully
        failures: dict {trader: Exception}
    """
    traders = [master_obj, *child_objs]
    successes = []
    failures = {}
    
    def _safe_auth(trader):
        trader.authenticate()           # may raise
        return trader                   # return the trader itself if ok

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {pool.submit(_safe_auth, t): t for t in traders}
        for fut in as_completed(future_map):
            trader = future_map[fut]
            try:
                result_trader = fut.result()
                successes.append(result_trader)
                if callable(on_result):
                    on_result(result_trader, True, None)
            except Exception as e:
                failures[trader] = e
                if callable(on_status):
                    on_status(f"AUTH ERROR {getattr(trader, 'name', getattr(trader, 'CLIENT', '-'))}: {e}")
                if callable(on_result):
                    on_result(trader, False, e)

    if callable(on_status):
        on_status("All accounts authenticated and done")

    return successes, failures

