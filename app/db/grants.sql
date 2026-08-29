-- Run once as the schema owner after `make migrate`, replacing cart_app with the runtime role.
-- The runtime role gets data access only; schema changes stay with the owner role.
GRANT USAGE ON SCHEMA public TO cart_app;
GRANT SELECT ON products, product_embeddings TO cart_app;
GRANT UPDATE (stock) ON products TO cart_app;
GRANT SELECT, INSERT, UPDATE ON sessions, orders, order_lines, llm_usage TO cart_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON checkpoints, checkpoint_blobs, checkpoint_writes TO cart_app;
GRANT SELECT ON checkpoint_migrations TO cart_app;
GRANT USAGE ON SEQUENCE order_number_seq TO cart_app;
