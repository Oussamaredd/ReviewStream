ANALYTICS_ROW_FILTER = "(product_id IS NULL OR UPPER(product_id) NOT LIKE 'E2E%')"
OPINION_TEXT_FILTER = "(text IS NOT NULL AND LENGTH(TRIM(text)) > 0)"

SUMMARY_QUERY = """
    SELECT
        COUNT(*) AS total_reviews,
        AVG(score) AS average_score,
        MIN(created_at) AS first_review_at,
        MAX(created_at) AS last_review_at
    FROM reviews_enriched
    WHERE {row_filter}
    """.format(row_filter=ANALYTICS_ROW_FILTER)

SENTIMENT_COUNTS_QUERY = """
    SELECT
        sentiment,
        COUNT(*) AS review_count
    FROM reviews_enriched
    WHERE {row_filter}
    GROUP BY sentiment
    ORDER BY sentiment
    """.format(row_filter=ANALYTICS_ROW_FILTER)

SCORE_DISTRIBUTION_QUERY = """
    SELECT
        score,
        COUNT(*) AS review_count
    FROM reviews_enriched
    WHERE {row_filter}
    GROUP BY score
    ORDER BY score
    """.format(row_filter=ANALYTICS_ROW_FILTER)

PRODUCT_SCORES_QUERY_TEMPLATE = """
    SELECT
        product_id,
        COUNT(*) AS review_count,
        AVG(score) AS average_score
    FROM reviews_enriched
    WHERE {row_filter}
    GROUP BY product_id
    ORDER BY review_count DESC, average_score DESC
    LIMIT {limit}
    """

RANKED_PRODUCTS_QUERY_TEMPLATE = """
    SELECT
        product_id,
        COUNT(*) AS review_count,
        AVG(score) AS average_score
    FROM reviews_enriched
    WHERE {row_filter}
    GROUP BY product_id
    HAVING COUNT(*) >= {min_reviews}
    ORDER BY average_score {direction}, review_count DESC
    LIMIT {limit}
    """

RECENT_REVIEWS_QUERY_TEMPLATE = """
    SELECT
        product_id,
        user_id,
        score,
        sentiment,
        text,
        source,
        review_id,
        created_at,
        text_length,
        word_count,
        has_negative_keywords,
        has_positive_keywords
    FROM reviews_enriched
    WHERE created_at IS NOT NULL
        AND {row_filter}
        AND {text_filter}
    ORDER BY created_at DESC
    LIMIT {limit}
    """

OPINIONS_QUERY_TEMPLATE = """
    SELECT
        product_id,
        user_id,
        score,
        sentiment,
        text,
        source,
        review_id,
        created_at,
        text_length,
        word_count,
        has_negative_keywords,
        has_positive_keywords
    FROM reviews_enriched
    {where_clause}
    ORDER BY created_at DESC
    LIMIT {limit}
    """

NEGATIVE_PRODUCTS_QUERY_TEMPLATE = """
    SELECT
        product_id,
        SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_review_count,
        COUNT(*) AS review_count,
        AVG(score) AS average_score
    FROM reviews_enriched
    WHERE {row_filter}
    GROUP BY product_id
    HAVING COUNT(*) >= {min_reviews}
        AND SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) > 0
    ORDER BY negative_review_count DESC, average_score ASC
    LIMIT {limit}
    """

SOURCES_QUERY = """
    SELECT
        COALESCE(source, 'unknown') AS source,
        COUNT(*) AS review_count
    FROM reviews_enriched
    WHERE {row_filter}
    GROUP BY COALESCE(source, 'unknown')
    ORDER BY review_count DESC, source
    """.format(row_filter=ANALYTICS_ROW_FILTER)

NEGATIVE_KEYWORD_COUNT_QUERY = """
    SELECT
        COUNT(*) AS matching_reviews
    FROM reviews_enriched
    WHERE has_negative_keywords = true
        AND {row_filter}
        AND {text_filter}
    """.format(row_filter=ANALYTICS_ROW_FILTER, text_filter=OPINION_TEXT_FILTER)

POSITIVE_KEYWORD_COUNT_QUERY = """
    SELECT
        COUNT(*) AS matching_reviews
    FROM reviews_enriched
    WHERE has_positive_keywords = true
        AND {row_filter}
        AND {text_filter}
    """.format(row_filter=ANALYTICS_ROW_FILTER, text_filter=OPINION_TEXT_FILTER)
