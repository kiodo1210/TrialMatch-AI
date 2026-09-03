import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analytics.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_hash TEXT NOT NULL,
            client_ip TEXT,
            user_agent TEXT,
            path TEXT NOT NULL,
            method TEXT NOT NULL,
            status_code INTEGER DEFAULT 200,
            duration_ms REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matching_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gene_variant TEXT,
            disease_name TEXT,
            clinical_stage TEXT,
            ip_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pv_created_at ON page_views (created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pv_ip_hash ON page_views (ip_hash)")
    conn.commit()
    conn.close()

init_db()

def _hash_ip(ip: str, user_agent: str = "") -> str:
    raw = f"{ip}_{user_agent}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

def record_visit(client_ip: str, user_agent: str, path: str, method: str = "GET", status_code: int = 200, duration_ms: float = 0.0):
    # Static files and favicon filtering can be handled if needed
    if path.startswith("/static") or path == "/favicon.ico":
        return
    
    ip_hash = _hash_ip(client_ip, user_agent)
    # Mask last octet for privacy: e.g. 192.168.1.xxx or 127.0.0.1
    masked_ip = ".".join(client_ip.split(".")[:-1] + ["xxx"]) if "." in client_ip else client_ip

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO page_views (ip_hash, client_ip, user_agent, path, method, status_code, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ip_hash, masked_ip, user_agent[:200] if user_agent else "", path, method, status_code, round(duration_ms, 2)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Analytics Error] Failed to record visit: {e}")

def record_matching_event(gene_variant: str, disease_name: str, clinical_stage: str, client_ip: str = ""):
    ip_hash = _hash_ip(client_ip)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO matching_events (gene_variant, disease_name, clinical_stage, ip_hash)
            VALUES (?, ?, ?, ?)
        """, (gene_variant, disease_name, clinical_stage, ip_hash))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Analytics Error] Failed to record matching event: {e}")

def get_analytics_summary() -> Dict[str, Any]:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Total Visits & Unique Visitors
        cursor.execute("SELECT COUNT(*) as total_views, COUNT(DISTINCT ip_hash) as unique_visitors FROM page_views")
        row = cursor.fetchone()
        total_views = row["total_views"] if row else 0
        unique_visitors = row["unique_visitors"] if row else 0

        # 2. Today's Stats (UTC/Local)
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) as today_views, COUNT(DISTINCT ip_hash) as today_uniques 
            FROM page_views 
            WHERE date(created_at) = date('now')
        """)
        today_row = cursor.fetchone()
        today_views = today_row["today_views"] if today_row else 0
        today_uniques = today_row["today_uniques"] if today_row else 0

        # 3. Active in last 5 minutes (Real-time active visitors)
        cursor.execute("""
            SELECT COUNT(DISTINCT ip_hash) as active_now 
            FROM page_views 
            WHERE created_at >= datetime('now', '-5 minutes')
        """)
        active_row = cursor.fetchone()
        active_now = max(1, active_row["active_now"]) if active_row and active_row["active_now"] > 0 else 0

        # 4. Total Matching AI Pipeline Runs
        cursor.execute("SELECT COUNT(*) as total_matches FROM matching_events")
        matches_row = cursor.fetchone()
        total_matches = matches_row["total_matches"] if matches_row else 0

        # 5. Recent Visits (Last 15)
        cursor.execute("""
            SELECT client_ip, path, method, status_code, duration_ms, created_at, user_agent
            FROM page_views 
            ORDER BY created_at DESC 
            LIMIT 15
        """)
        recent_visits = [dict(r) for r in cursor.fetchall()]

        # 6. Popular Pages
        cursor.execute("""
            SELECT path, COUNT(*) as hit_count 
            FROM page_views 
            GROUP BY path 
            ORDER BY hit_count DESC 
            LIMIT 5
        """)
        popular_pages = [dict(r) for r in cursor.fetchall()]

        # 7. Daily Trend (Last 7 days)
        cursor.execute("""
            SELECT date(created_at) as visit_date, COUNT(*) as view_count, COUNT(DISTINCT ip_hash) as unique_count
            FROM page_views
            WHERE created_at >= date('now', '-7 days')
            GROUP BY date(created_at)
            ORDER BY visit_date ASC
        """)
        daily_trends = [dict(r) for r in cursor.fetchall()]

        conn.close()

        return {
            "status": "SUCCESS",
            "active_now": active_now,
            "today_views": today_views,
            "today_uniques": today_uniques,
            "total_views": total_views,
            "unique_visitors": unique_visitors,
            "total_matches": total_matches,
            "popular_pages": popular_pages,
            "daily_trends": daily_trends,
            "recent_visits": recent_visits
        }
    except Exception as e:
        print(f"[Analytics Error] Summary generation error: {e}")
        return {
            "status": "ERROR",
            "error": str(e),
            "active_now": 0,
            "today_views": 0,
            "today_uniques": 0,
            "total_views": 0,
            "unique_visitors": 0,
            "total_matches": 0,
            "recent_visits": []
        }
