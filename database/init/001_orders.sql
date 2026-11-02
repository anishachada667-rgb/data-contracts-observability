CREATE SCHEMA IF NOT EXISTS source;

CREATE TABLE IF NOT EXISTS source.orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    order_amount NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO source.orders (
    order_id,
    customer_id,
    order_status,
    order_amount,
    created_at
)
SELECT
    n,
    ((n - 1) % 200) + 1,
    CASE
        WHEN n % 10 = 0 THEN 'CANCELLED'
        WHEN n % 4 = 0 THEN 'PROCESSING'
        ELSE 'COMPLETED'
    END,
    (10 + (n % 490) + ((n % 100)::NUMERIC / 100))::NUMERIC(12, 2),
    CURRENT_TIMESTAMP - (n * INTERVAL '1 minute')
FROM generate_series(1, 1000) AS n
ON CONFLICT (order_id) DO NOTHING;