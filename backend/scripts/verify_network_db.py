"""PostgreSQL verification script for Phase 4 Network Analysis (§27)."""

from sqlalchemy import text
from app.db.session import SessionLocal

def main():
    db = SessionLocal()
    try:
        # Latest global run ID
        run_id_global = db.execute(text("SELECT max(id) FROM network_analysis_runs WHERE scope_type = 'global'")).scalar()
        # Latest topic run ID
        run_id_topic = db.execute(text("SELECT max(id) FROM network_analysis_runs WHERE scope_type = 'topic'")).scalar()

        print("=" * 95)
        print(f"=== A. TOP INFLUENCERS BY PAGERANK (Global Run {run_id_global}) ===")
        print("=" * 95)
        qA = text(f"""
            SELECT u.username, n.pagerank_score, n.in_degree, n.weighted_in_degree, n.community_id
            FROM network_nodes n
            JOIN users u ON n.user_id = u.id
            WHERE n.run_id = {run_id_global}
            ORDER BY n.pagerank_score DESC
            LIMIT 10
        """)
        for r in db.execute(qA):
            print(f"@{r.username:<24} | PageRank: {r.pagerank_score:.6f} | In-Degree: {r.in_degree:2d} (Vol: {r.weighted_in_degree:4.1f}) | Community: {r.community_id}")

        print("\n" + "=" * 95)
        print(f"=== B. TOP BRIDGES BY BETWEENNESS CENTRALITY (Global Run {run_id_global}) ===")
        print("=" * 95)
        qB = text(f"""
            SELECT u.username, n.betweenness_centrality, n.cross_community_edge_count, n.communities_reached, n.community_id
            FROM network_nodes n
            JOIN users u ON n.user_id = u.id
            WHERE n.run_id = {run_id_global}
            ORDER BY n.betweenness_centrality DESC, n.cross_community_edge_count DESC
            LIMIT 10
        """)
        for r in db.execute(qB):
            print(f"@{r.username:<24} | Betweenness: {r.betweenness_centrality:.6f} | Cross Edges: {r.cross_community_edge_count:2d} | Comm Reached: {r.communities_reached:2d} | Comm: {r.community_id}")

        print("\n" + "=" * 95)
        print(f"=== C. LOUVAIN COMMUNITIES DISTRIBUTION (Global Run {run_id_global}) ===")
        print("=" * 95)
        qC = text(f"""
            SELECT n.community_id, count(n.id) as user_count
            FROM network_nodes n
            WHERE n.run_id = {run_id_global}
            GROUP BY n.community_id
            ORDER BY user_count DESC, n.community_id ASC
            LIMIT 10
        """)
        for r in db.execute(qC):
            print(f"Community {r.community_id:3d} | User Count: {r.user_count:3d}")

        print("\n" + "=" * 95)
        print(f"=== D. NETWORK EDGES (Sample Aggregated Pairwise Interactions, Global Run {run_id_global}) ===")
        print("=" * 95)
        qD = text(f"""
            SELECT u1.username as src, u2.username as tgt, e.total_weight, e.reply_count, e.mention_count, e.repost_count, e.quote_count
            FROM network_edges e
            JOIN users u1 ON e.source_user_id = u1.id
            JOIN users u2 ON e.target_user_id = u2.id
            WHERE e.run_id = {run_id_global}
            ORDER BY e.total_weight DESC
            LIMIT 10
        """)
        for r in db.execute(qD):
            print(f"@{r.src:<20} -> @{r.tgt:<20} | Weight: {r.total_weight:3.1f} | Reply: {r.reply_count} Ment: {r.mention_count} Repost: {r.repost_count} Quote: {r.quote_count}")

        print("\n" + "=" * 95)
        print(f"=== E. OBSERVED COMMUNITY FLOWS (Global Run {run_id_global}) ===")
        print("=" * 95)
        qE = text(f"""
            SELECT source_community_id, target_community_id, interaction_count, first_observed_at, last_observed_at
            FROM community_flows
            WHERE run_id = {run_id_global}
            ORDER BY interaction_count DESC
            LIMIT 10
        """)
        for r in db.execute(qE):
            t_str = r.first_observed_at.strftime("%Y-%m-%d %H:%M") if r.first_observed_at else "N/A"
            print(f"Comm {r.source_community_id:3d} -> Comm {r.target_community_id:3d} | Interactions: {r.interaction_count:3d} | Observed: {t_str}")

        if run_id_topic:
            print("\n" + "=" * 95)
            print(f"=== F. TOPIC NETWORK + COMMUNITY SENTIMENT BREAKDOWN (Topic Run {run_id_topic}) ===")
            print("=" * 95)
            qF = text(f"""
                SELECT t.label as topic_label, n.community_id, sr.final_sentiment, count(*) as tweet_count
                FROM network_analysis_runs r
                JOIN topics t ON r.topic_id = t.id
                JOIN network_nodes n ON r.id = n.run_id
                JOIN tweets tw ON n.user_id = tw.author_id
                JOIN tweet_topics tt ON tw.id = tt.tweet_id AND tt.topic_id = r.topic_id AND tt.is_outlier = false
                JOIN sentiment_results sr ON tw.id = sr.tweet_id
                WHERE r.id = {run_id_topic}
                GROUP BY t.label, n.community_id, sr.final_sentiment
                ORDER BY n.community_id, sr.final_sentiment
                LIMIT 20
            """)
            current_comm = None
            for r in db.execute(qF):
                if r.community_id != current_comm:
                    current_comm = r.community_id
                    print(f"\nTopic: '{r.topic_label}' | Community {r.community_id}:")
                print(f"    {r.final_sentiment:8s}: {r.tweet_count:2d} tweets")
        print("\n" + "=" * 95)

    finally:
        db.close()

if __name__ == "__main__":
    main()
