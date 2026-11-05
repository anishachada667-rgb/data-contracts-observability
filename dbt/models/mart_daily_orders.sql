{{
    config(materialized='table')
}}

select
    cast(created_at as date) as order_date,
    order_status,
    count(*) as order_count,
    sum(order_amount) as total_order_amount
from {{ ref('stg_orders') }}
group by
    cast(created_at as date),
    order_status