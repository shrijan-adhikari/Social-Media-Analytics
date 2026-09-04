"""Database verification script for Phase 3A Trend & Topic Detection."""

from sqlalchemy import text
from app.db.session import SessionLocal

def main():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("=== 1. TOP TOPICS IN POSTGRESQL (Latest Analysis Run) ===")
        print("=" * 80)
        q1 = text("""
            SELECT t.id, t.topic_type, t.label, t.representative_terms::text as rep_terms_txt, count(tt.id) as tweet_count 
            FROM topics t 
            JOIN tweet_topics tt ON t.id = tt.topic_id 
            WHERE t.run_id = (SELECT max(id) FROM trend_analysis_runs) 
            GROUP BY t.id, t.topic_type, t.label, t.representative_terms::text 
            ORDER BY tweet_count DESC
        """)
        for r in db.execute(q1):
            print(f"ID {r.id:2d} | [{r.topic_type.upper():8s}] {r.label[:35]:35s} | {r.tweet_count:3d} tweets | Terms: {r.rep_terms_txt}")

        print("\n" + "=" * 80)
        print("=== 2. TOP EMERGING TREND WINDOWS (Velocity & Acceleration) ===")
        print("=" * 80)
        q2 = text("""
            SELECT tw.id, t.label, tw.window_start, tw.window_end, 
                   tw.mention_count, tw.baseline_mentions, tw.velocity, tw.acceleration, 
                   tw.like_count, tw.repost_count, tw.reply_count
            FROM trend_windows tw 
            JOIN topics t ON tw.topic_id = t.id 
            WHERE tw.run_id = (SELECT max(id) FROM trend_analysis_runs) AND tw.velocity > 0 
            ORDER BY tw.velocity DESC, tw.mention_count DESC 
            LIMIT 10
        """)
        for r in db.execute(q2):
            w_str = f"{r.window_start.strftime('%Y-%m-%d %H:%M')} - {r.window_end.strftime('%H:%M')} UTC"
            print(f"Topic: {r.label[:30]:30s} | Window: {w_str} | Mentions: {r.mention_count:2d} (Base: {r.baseline_mentions:4.2f}) | Vel: {r.velocity:5.2f}x | Accel: {r.acceleration:+5.2f} | Likes: {r.like_count:2d} Reposts: {r.repost_count:2d}")

        print("\n" + "=" * 80)
        print("=== 3. TOPIC + READ-ONLY SENTIMENT BREAKDOWN ===")
        print("=" * 80)
        q3 = text("""
            SELECT t.label, t.topic_type, sr.final_sentiment, count(*) as count 
            FROM topics t 
            JOIN tweet_topics tt ON t.id = tt.topic_id 
            JOIN sentiment_results sr ON tt.tweet_id = sr.tweet_id 
            WHERE t.run_id = (SELECT max(id) FROM trend_analysis_runs) 
            GROUP BY t.label, t.topic_type, sr.final_sentiment 
            ORDER BY t.label, sr.final_sentiment
        """)
        current_topic = None
        for r in db.execute(q3):
            if r.label != current_topic:
                current_topic = r.label
                print(f"\n[{r.topic_type.upper()}] {r.label}:")
            print(f"    {r.final_sentiment:8s}: {r.count:2d}")
        print("=" * 80 + "\n")
    finally:
        db.close()

if __name__ == "__main__":
    main()
