"""14 запросов самостоятельной работы (pizza_orders.db). Запросы проверяются на SQLite; в Loginom вставляются как есть.
order_datetime хранится как юлианская дата (REAL), поэтому везде datetime()/date()/time()/strftime()."""
import sqlite3, sys
Q = [
 ("1. HAVING (пример: категории, где продано больше 10 000 пицц)",
  """SELECT c.category_name, SUM(od.quantity) AS total_qty
FROM order_details od
JOIN pizza_size ps USING(pizza_size_id)
JOIN pizza p USING(pizza_id)
JOIN category c ON c.category_id = p.category_id
GROUP BY c.category_name
HAVING SUM(od.quantity) > 10000;"""),
 ("2. Имена таблиц и их запросы (sqlite_schema)",
  """SELECT name, sql
FROM sqlite_schema
WHERE type = 'table';"""),
 ("3. Названия пицц и ингредиенты",
  """SELECT pizza_name, pizza_ingredients
FROM pizza;"""),
 ("4. Veggie или Chicken, с ингредиентами",
  """SELECT p.pizza_name, c.category_name, p.pizza_ingredients
FROM pizza p
JOIN category c ON c.category_id = p.category_id
WHERE c.category_name IN ('Veggie', 'Chicken');"""),
 ("5. Пиццы с моцареллой, с ингредиентами и категорией",
  """SELECT p.pizza_name, p.pizza_ingredients, c.category_name
FROM pizza p
JOIN category c ON c.category_id = p.category_id
WHERE p.pizza_ingredients LIKE '%Mozzarella Cheese%';"""),
 ("6. Заказы с 01.04.2015 (вкл.) по 01.08.2015 (не вкл.), время с 13:00 до 17:00",
  """SELECT order_id
FROM orders
WHERE date(order_datetime) >= '2015-04-01'
  AND date(order_datetime) <  '2015-08-01'
  AND time(order_datetime) >= '13:00:00'
  AND time(order_datetime) <= '17:00:00'
ORDER BY order_id;"""),
 ("7. Топ-10 заказов по количеству купленных пицц",
  """SELECT order_id, SUM(quantity) AS pizza_count
FROM order_details
GROUP BY order_id
ORDER BY pizza_count DESC
LIMIT 10;"""),
 ("8. Дата и время 10 заказов с наибольшим числом пицц",
  """SELECT o.order_id,
       date(o.order_datetime) AS order_date,
       time(o.order_datetime) AS order_time,
       SUM(od.quantity) AS pizza_count
FROM orders o
JOIN order_details od USING(order_id)
GROUP BY o.order_id
ORDER BY pizza_count DESC, order_date ASC, order_time ASC
LIMIT 10;"""),
 ("9. Полное меню: название, размер, цена, категория, ингредиенты",
  """SELECT p.pizza_name, s.size_name, ps.unit_price, c.category_name, p.pizza_ingredients
FROM pizza_size ps
JOIN pizza p USING(pizza_id)
JOIN size s USING(size_id)
JOIN category c ON c.category_id = p.category_id
ORDER BY p.pizza_name, s.size_id;"""),
 ("10. Сколько раз позиция меню куплена не в единственном экземпляре",
  """SELECT p.pizza_name, s.size_name, COUNT(*) AS times_bought_more_than_one
FROM order_details od
JOIN pizza_size ps USING(pizza_size_id)
JOIN pizza p USING(pizza_id)
JOIN size s USING(size_id)
WHERE od.quantity != 1
GROUP BY p.pizza_name, s.size_name
ORDER BY times_bought_more_than_one DESC;"""),
 ("11. Полная таблица транзакций (всё в одной)",
  """SELECT od.order_details_id, o.order_id,
       date(o.order_datetime) AS order_date,
       time(o.order_datetime) AS order_time,
       p.pizza_name, c.category_name, p.pizza_ingredients, s.size_name,
       ps.unit_price, od.quantity,
       od.quantity * ps.unit_price AS total_price
FROM order_details od
JOIN orders o USING(order_id)
JOIN pizza_size ps USING(pizza_size_id)
JOIN pizza p USING(pizza_id)
JOIN size s USING(size_id)
JOIN category c ON c.category_id = p.category_id;"""),
 ("12. Представление на таблицу из задания 11",
  """CREATE VIEW IF NOT EXISTS v_transactions AS
SELECT od.order_details_id, o.order_id,
       date(o.order_datetime) AS order_date,
       time(o.order_datetime) AS order_time,
       p.pizza_name, c.category_name, p.pizza_ingredients, s.size_name,
       ps.unit_price, od.quantity,
       od.quantity * ps.unit_price AS total_price
FROM order_details od
JOIN orders o USING(order_id)
JOIN pizza_size ps USING(pizza_size_id)
JOIN pizza p USING(pizza_id)
JOIN size s USING(size_id)
JOIN category c ON c.category_id = p.category_id;"""),
 ("13. Доход по категориям, по убыванию, округление до 2 знаков",
  """SELECT c.category_name, ROUND(SUM(od.quantity * ps.unit_price), 2) AS revenue
FROM order_details od
JOIN pizza_size ps USING(pizza_size_id)
JOIN pizza p USING(pizza_id)
JOIN category c ON c.category_id = p.category_id
GROUP BY c.category_name
ORDER BY revenue DESC;"""),
 ("14. Размер, проданный больше всего в 3-м и в 4-м кварталах 2015",
  """SELECT quarter, size_name, qty FROM (
  SELECT CASE WHEN CAST(strftime('%m', o.order_datetime) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3' ELSE 'Q4' END AS quarter,
         s.size_name, SUM(od.quantity) AS qty,
         ROW_NUMBER() OVER (PARTITION BY CASE WHEN CAST(strftime('%m', o.order_datetime) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3' ELSE 'Q4' END
                            ORDER BY SUM(od.quantity) DESC) AS rn
  FROM order_details od
  JOIN orders o USING(order_id)
  JOIN pizza_size ps USING(pizza_size_id)
  JOIN size s USING(size_id)
  WHERE CAST(strftime('%m', o.order_datetime) AS INTEGER) BETWEEN 7 AND 12
  GROUP BY quarter, s.size_name
) WHERE rn = 1
ORDER BY quarter;"""),
]
if __name__ == '__main__':
    db = sys.argv[1]
    c = sqlite3.connect(':memory:'); src = sqlite3.connect(db); src.backup(c)   # работаем на копии в памяти
    for title, q in Q:
        cur = c.execute(q); rows = cur.fetchall()
        print(f"\n## {title}\nстрок: {len(rows)}")
        if cur.description: print([d[0] for d in cur.description])
        for r in rows[:5]: print(r)
