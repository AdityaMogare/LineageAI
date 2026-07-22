select
    p.category,
    c.region,
    sum(oi.quantity * p.price) as gross_item_revenue,
    count(distinct pay.payment_id) as payment_count
from main.orders o
join main.customers c on c.customer_id = o.customer_id
join main.order_items oi on oi.order_id = o.id
join main.products p on p.product_id = oi.product_id
left join main.payments pay on pay.order_id = o.id
group by p.category, c.region
