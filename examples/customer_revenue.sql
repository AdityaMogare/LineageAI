select
    c.customer_id,
    c.region,
    sum(o.amount) as total_revenue,
    count(*) as order_count
from main.customers as c
inner join main.orders as o
    on c.customer_id = o.customer_id
group by c.customer_id, c.region
