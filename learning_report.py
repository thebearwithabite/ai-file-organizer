#!/usr/bin/env python3
"""
AI Intelligence Learning Report
Generates a summary of the system's learning progress and active thought patterns.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from gdrive_integration import get_metadata_root

def generate_report():
    db_path = get_metadata_root() / "databases" / "adaptive_learning.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print("🧠 AI Intelligence Learning Report")
    print("=" * 60)
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 1. High Level Stats
            total_events = conn.execute("SELECT COUNT(*) FROM learning_events").fetchone()[0]
            verified_events = conn.execute("SELECT COUNT(*) FROM learning_events WHERE event_type IN ('user_correction', 'manual_move', 'preference_update', 'user_confirmed')").fetchone()[0]
            observations = conn.execute("SELECT COUNT(*) FROM learning_events WHERE event_type = 'ai_observation'").fetchone()[0]
            
            print(f"📈 Knowledge Base Stats:")
            print(f"   Total Learning Events:  {total_events}")
            print(f"   Verified Interactions:  {verified_events}")
            print(f"   AI Self-Observations:   {observations}")
            
            # 2. Pattern Discovery
            patterns = conn.execute("SELECT pattern_type, COUNT(*) as count FROM patterns GROUP BY pattern_type").fetchall()
            print(f"\n🧠 Active Thought Patterns:")
            for p in patterns:
                print(f"   • {p['pattern_type'].capitalize()}-based: {p['count']} rules")
            
            # 3. Top Categories (Intelligence Center)
            print(f"\n🏷️  Top 5 Intelligent Clusters:")
            
            # First try verified
            cat_query_verified = """
                SELECT json_extract(user_action, '$.target_category') as category, COUNT(*) as count 
                FROM learning_events 
                WHERE event_type IN ('user_correction', 'manual_move', 'user_confirmed')
                AND category IS NOT NULL
                GROUP BY category 
                ORDER BY count DESC 
                LIMIT 5
            """
            categories = conn.execute(cat_query_verified).fetchall()
            
            if not categories:
                # Fallback to observations
                cat_query_obs = """
                    SELECT json_extract(original_prediction, '$.category') as category, COUNT(*) as count 
                    FROM learning_events 
                    WHERE event_type = 'ai_observation'
                    AND category IS NOT NULL
                    GROUP BY category 
                    ORDER BY count DESC 
                    LIMIT 5
                """
                categories = conn.execute(cat_query_obs).fetchall()
                print("   (Based on AI Observations - no confirmed data yet)")

            for c in categories:
                print(f"   • {c['category']}: {c['count']} decisions")

            # 4. Recent Accuracy Improvement
            print(f"\n⚡ Accuracy & Confidence Trends:")
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            row = conn.execute("SELECT AVG(confidence_after) FROM learning_events WHERE timestamp > ?", (cutoff,)).fetchone()
            recent_conf = row[0] if row else None
            
            if recent_conf:
                print(f"   • Avg. Confidence (7d): {recent_conf:.2f}")
            else:
                print("   • Not enough data for 7-day trend")

    except Exception as e:
        print(f"❌ Error generating report: {e}")

if __name__ == "__main__":
    generate_report()
