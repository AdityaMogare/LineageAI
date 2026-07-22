select
    c.customer_id,
    c.region,
    sum(o.amount) as total_revenue
from main.customers c
join main.orders o on o.customer_id = c.customer_id
group by c.customer_id, c.region
