"""
Fofoqueiro – Worker (Agendamento e Extração Paralelizada)
"""
import time
import fcntl
import sys
import os
import schedule
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import config
import database
from ai_service import summarize
from fetchers import HNFetcher, CVEFetcher, LWNFetcher, LinuxCVEAnnounceFetcher

LOG_FILE = f"{config.PROJECT_ROOT}/fofoqueiro.log"
LOCK_FILE = f"{config.PROJECT_ROOT}/worker.lock"
_lock_fd = None

def acquire_lock():
    """Garante execução atômica via lock exclusivo de arquivo (fcntl)."""
    global _lock_fd
    try:
        _lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fd.write(str(os.getpid()))
        _lock_fd.flush()
        return True
    except (BlockingIOError, IOError):
        return False

def release_lock():
    """Libera o lock do arquivo."""
    global _lock_fd
    if _lock_fd:
        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            _lock_fd.close()
        except Exception:
            pass

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def process_pending_summaries():
    log("AI Service: processando resumos pendentes...")
    conn = database.get_connection()
    pending = database.get_pending(conn, limit=20)
    if not pending:
        log("Nenhuma notícia aguardando processamento de IA.")
        conn.close()
        return

    processed_count = 0
    for item in pending:
        if item["processed"] == 1:
            continue
            
        log(f"  [AI] Sintetizando: {item['title'][:60]}... ({item['source']})")
        title_clean, summary = summarize(item["title"], item["summary"] or "", item["source"])
        database.update_summary(conn, item["id"], title_clean, summary)
        processed_count += 1
        time.sleep(0.5) # Rate limit suave
    
    conn.close()
    log(f"Processamento de resumos finalizado. ({processed_count} sintetizadas)")

def _run_single_fetcher(fetcher_obj):
    source = fetcher_obj.source_name
    conn = database.get_connection()
    run_id = database.start_run(conn, source)
    try:
        items = fetcher_obj.fetch()
        new_items = database.upsert_news(conn, items)
        database.finish_run(conn, run_id, len(items), new_items)
        log(f"  [{source.upper()}] Coleta concluída: {len(items)} encontradas, {new_items} novas.")
    except Exception as e:
        log(f"  [{source.upper()}] Erro na coleta: {e}")
    finally:
        conn.close()

def run_fetchers():
    log("Iniciando ciclo de coletas paralelizadas...")
    conn = database.get_connection()
    database.init_db(conn)
    conn.close()

    fetchers = [
        HNFetcher(config.HN_TOP_STORIES_URL, config.HN_ITEM_URL, config.HN_FETCH_LIMIT),
        CVEFetcher(config.CVE_FEEDS, theme_keywords=config.THEME_KEYWORDS),
        LWNFetcher(rss_url=config.LWN_RSS_URL, limit=30),
        LinuxCVEAnnounceFetcher(theme_keywords=config.THEME_KEYWORDS)
    ]

    # Parallelize fetchers execution
    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = [executor.submit(_run_single_fetcher, f) for f in fetchers]
        for future in as_completed(futures):
            future.result()

    log("Coletas paralelizadas concluídas.")

    # Inicia processamento de IA após as coletas
    process_pending_summaries()

def main():
    if not acquire_lock():
        print("⚠️ Outra instância do worker já está em execução. Saindo.")
        sys.exit(1)

    log(f"=== Iniciando Fofoqueiro Worker Daemon (PID {os.getpid()}) ===")
    
    try:
        # Executa primeira rodada
        run_fetchers()

        # Agenda execuções recorrentes
        schedule.every(config.WORKER_INTERVAL_MINUTES).minutes.do(run_fetchers)

        while True:
            schedule.run_pending()
            time.sleep(5)
    except KeyboardInterrupt:
        log("Worker interrompido pelo usuário.")
    finally:
        release_lock()
        log("Lock liberado. Worker encerrado.")

if __name__ == "__main__":
    main()
