from psycopg_pool import AsyncConnectionPool

from app.order.pricing import Cart


class OutOfStockError(Exception):
    def __init__(self, product_name: str) -> None:
        super().__init__(f"{product_name} is out of stock for the requested quantity")
        self.product_name = product_name


_ORDERS_SQL = """
SELECT o.id, o.session_id, o.subtotal_cents, o.shipping_cents, o.tax_cents, o.total_cents,
       o.cart_hash, o.status, o.created_at,
       coalesce(
           json_agg(json_build_object(
               'product_id', l.product_id, 'name', l.name, 'category', l.category,
               'quantity', l.quantity, 'unit_price_cents', l.unit_price_cents
           ) ORDER BY l.product_id) FILTER (WHERE l.order_id IS NOT NULL),
           '[]'
       ) AS lines
FROM orders o
LEFT JOIN order_lines l ON l.order_id = o.id
WHERE o.session_id = %(session_id)s AND (%(order_id)s::text IS NULL OR o.id = %(order_id)s)
GROUP BY o.id
ORDER BY o.created_at DESC
"""


class OrderRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def place(self, session_id: str, cart: Cart) -> dict:
        async with self._pool.connection() as conn, conn.transaction():
            for line in cart["lines"]:
                reserved = await (
                    await conn.execute(
                        "UPDATE products SET stock = stock - %s WHERE id = %s AND stock >= %s RETURNING id",
                        (line["quantity"], line["product_id"], line["quantity"]),
                    )
                ).fetchone()
                if reserved is None:
                    raise OutOfStockError(line["name"])
            order = await (
                await conn.execute(
                    """
                    INSERT INTO orders
                        (session_id, subtotal_cents, shipping_cents, tax_cents, total_cents, cart_hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        session_id,
                        cart["subtotal_cents"],
                        cart["shipping_cents"],
                        cart["tax_cents"],
                        cart["total_cents"],
                        cart["cart_hash"],
                    ),
                )
            ).fetchone()
            async with conn.cursor() as cur:
                await cur.executemany(
                    """
                    INSERT INTO order_lines (order_id, product_id, name, category, quantity, unit_price_cents)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            order["id"],
                            line["product_id"],
                            line["name"],
                            line["category"],
                            line["quantity"],
                            line["unit_price_cents"],
                        )
                        for line in cart["lines"]
                    ],
                )
        return await self.get(session_id, order["id"])

    async def find_by_session(self, session_id: str) -> list[dict]:
        async with self._pool.connection() as conn:
            return await (
                await conn.execute(_ORDERS_SQL, {"session_id": session_id, "order_id": None})
            ).fetchall()

    async def get(self, session_id: str, order_id: str) -> dict | None:
        async with self._pool.connection() as conn:
            return await (
                await conn.execute(_ORDERS_SQL, {"session_id": session_id, "order_id": order_id})
            ).fetchone()

    async def cancel(self, session_id: str, order_id: str) -> dict:
        async with self._pool.connection() as conn, conn.transaction():
            cancelled = await (
                await conn.execute(
                    "UPDATE orders SET status = 'cancelled' "
                    "WHERE id = %s AND session_id = %s AND status = 'placed' RETURNING id",
                    (order_id, session_id),
                )
            ).fetchone()
            if cancelled is not None:
                await conn.execute(
                    "UPDATE products p SET stock = p.stock + l.quantity "
                    "FROM order_lines l WHERE l.order_id = %s AND l.product_id = p.id",
                    (order_id,),
                )
        return await self.get(session_id, order_id)

    async def request_return(self, session_id: str, order_id: str) -> dict:
        async with self._pool.connection() as conn:
            await conn.execute(
                "UPDATE orders SET status = 'return_requested' "
                "WHERE id = %s AND session_id = %s AND status = 'placed'",
                (order_id, session_id),
            )
        return await self.get(session_id, order_id)
