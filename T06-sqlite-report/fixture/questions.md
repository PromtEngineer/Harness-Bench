# Analytical questions for db/sales.db

Answer all five questions using only the data in `db/sales.db`
(tables: customers, products, orders, order_items).

Definitions used throughout — follow them exactly:

- **item revenue** = `quantity * unit_price` (from order_items).
- **order value** (also called order revenue) = sum of item revenue over all
  items of that order.
- **net** = excluding orders whose `status = 'refunded'`. All other statuses
  count.
- **month of an order** = the `YYYY-MM` prefix of `order_date`
  (i.e. `strftime('%Y-%m', order_date)`).
- **Rounding**: wherever a rounded value is requested, round with Python's
  built-in `round(x, 2)` (round-half-to-even). WARNING: SQLite's `ROUND()`
  rounds exact-.5 cases differently — do the final rounding in Python, e.g.
  `round(666.625, 2) == 666.62`.

## q1 — top customer

Which `customer_id` has the highest lifetime net revenue (sum of order value
over all of that customer's non-refunded orders)? Answer: an integer.
The maximum is unique.

## q2 — strongest growth month in 2025

Consider net monthly revenue (sum of order value of non-refunded orders per
month). For each month M of 2025 (2025-01 through 2025-12):

    growth(M) = net_revenue(M) - net_revenue(previous calendar month)

(for 2025-01 the previous month is 2024-12). Which month of 2025 has the
largest growth? Answer: that month as a string "YYYY-MM". The maximum is
unique.

## q3 — median order value per region

For each region, compute the median order value over that region's
non-refunded orders. Median definition: sort the values ascending; for an odd
count take the middle value; for an even count take the average of the two
middle values. Round each median with Python `round(median, 2)`.
Answer: an object mapping every region name to its rounded median.

## q4 — most co-purchased product pair

Which pair of two DISTINCT `product_id`s appears together in the greatest
number of distinct orders? Count over ALL orders regardless of status. Within
one order a product counts once even if it appears on several item lines.
Answer: the two product ids sorted ascending, as a JSON array `[a, b]`.
The maximum is unique.

## q5 — refund-adjusted total revenue

    q5 = (sum of order value over ALL orders)
         - (sum of order value over orders with status = 'refunded')

Round with Python `round(x, 2)`. Answer: a number.
