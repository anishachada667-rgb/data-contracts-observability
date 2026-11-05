{{
    config(
        materialized='table',
        contract={'enforced': true}
    )
}}

select
    cast(order_id as bigint) as order_id,
    cast(customer_id as bigint) as customer_id,
    cast(order_status as text) as order_status,
    cast(order_amount as numeric(12, 2)) as order_amount,
    cast(created_at as timestamp with time zone) as created_at,
    cast(loaded_at as timestamp with time zone) as loaded_at
from {{ source('retail_source', 'orders') }}