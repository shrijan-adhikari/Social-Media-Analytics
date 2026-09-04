"""PostgreSQL verification script for collection queries, runs, and provenance (§16)."""

from sqlalchemy import text
from app.db.session import SessionLocal

def main():
    db = SessionLocal()
    try:
        print("=" * 90)
        print("=== A. COLLECTION QUERIES (Configured in PostgreSQL) ===")
        print("=" * 90)
        qA = text("""
            SELECT id, query_key, category, query_text, is_enabled, default_limit 
            FROM collection_queries 
            ORDER BY category, query_key
        """)
        for r in db.execute(qA):
            print(f"ID {r.id:2d} | [{r.category:13s}] {r.query_key:24s} | Limit: {r.default_limit:2d} | Query: '{r.query_text}'")

        print("\n" + "=" * 90)
        print("=== B. COLLECTION RUNS (Executed Provenance Runs) ===")
        print("=" * 90)
        qB = text("""
            SELECT r.id, q.query_key, r.config_version, r.started_at, r.completed_at,
                   r.requested_limit, r.retrieved_count, r.inserted_count, r.duplicate_count, r.status
            FROM collection_runs r
            JOIN collection_queries q ON r.query_id = q.id
            ORDER BY r.id
        """)
        for r in db.execute(qB):
            s_str = r.started_at.strftime('%Y-%m-%d %H:%M:%S') if r.started_at else "N/A"
            c_str = r.completed_at.strftime('%H:%M:%S') if r.completed_at else "N/A"
            print(f"Run {r.id:2d} | Query: {r.query_key:23s} (v{r.config_version}) | Time: {s_str} - {c_str} UTC | Req: {r.requested_limit:2d} | Ret: {r.retrieved_count:2d} | Ins: {r.inserted_count:2d} | Dup: {r.duplicate_count:2d} | Status: {r.status.upper()}")

        print("\n" + "=" * 90)
        print("=== C. COLLECTION SOURCES (Sample Provenance Links) ===")
        print("=" * 90)
        qC = text("""
            SELECT s.tweet_id, t.twitter_tweet_id, LEFT(t.text, 55) as tweet_snippet, q.query_key, s.created_at
            FROM tweet_collection_sources s
            JOIN tweets t ON s.tweet_id = t.id
            JOIN collection_runs r ON s.collection_run_id = r.id
            JOIN collection_queries q ON r.query_id = q.id
            ORDER BY s.id DESC
            LIMIT 10
        """)
        for r in db.execute(qC):
            clean_snippet = r.tweet_snippet.replace('\n', ' ').encode('ascii', 'replace').decode('ascii')
            print(f"Tweet DB ID: {r.tweet_id:3d} (X: {r.twitter_tweet_id}) | Query: {r.query_key:23s} | Text: \"{clean_snippet}...\"")

        print("\n" + "=" * 90)
        print("=== D. MULTI-SOURCE EXAMPLE (Tweets Retrieved By Multiple Queries) ===")
        print("=" * 90)
        qD = text("""
            SELECT s.tweet_id, t.twitter_tweet_id, LEFT(t.text, 50) as tweet_snippet,
                   count(DISTINCT r.query_id) as distinct_query_count,
                   string_agg(DISTINCT q.query_key, ', ') as query_keys
            FROM tweet_collection_sources s
            JOIN tweets t ON s.tweet_id = t.id
            JOIN collection_runs r ON s.collection_run_id = r.id
            JOIN collection_queries q ON r.query_id = q.id
            GROUP BY s.tweet_id, t.twitter_tweet_id, t.text
            HAVING count(DISTINCT r.query_id) > 1
            ORDER BY distinct_query_count DESC
        """)
        multi_rows = list(db.execute(qD))
        if not multi_rows:
            print("No real multi-source tweets found in this sample run (disjoint queries evaluated).")
        else:
            for r in multi_rows:
                clean_snippet = r.tweet_snippet.replace('\n', ' ').encode('ascii', 'replace').decode('ascii')
                print(f"Tweet DB ID: {r.tweet_id:3d} (X: {r.twitter_tweet_id}) | Queries ({r.distinct_query_count}): [{r.query_keys}] | Text: \"{clean_snippet}...\"")
        print("=" * 90 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
