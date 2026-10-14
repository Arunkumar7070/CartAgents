CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS products (
    id text PRIMARY KEY,
    name text NOT NULL,
    category text NOT NULL,
    brand text NOT NULL,
    price_cents integer NOT NULL CHECK (price_cents >= 0),
    stock integer NOT NULL CHECK (stock >= 0),
    specs text NOT NULL,
    description text NOT NULL,
    search_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('english'::regconfig, name || ' ' || category || ' ' || brand || ' ' || specs || ' ' || description)
    ) STORED
);

CREATE INDEX IF NOT EXISTS products_search_tsv_idx ON products USING gin (search_tsv);

CREATE TABLE IF NOT EXISTS product_embeddings (
    product_id text NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    embedding_model text NOT NULL,
    embedding vector(768) NOT NULL,
    PRIMARY KEY (product_id, embedding_model)
);

CREATE TABLE IF NOT EXISTS sessions (
    id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    llm_calls integer NOT NULL DEFAULT 0
);

CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1000;

CREATE TABLE IF NOT EXISTS orders (
    id text PRIMARY KEY DEFAULT 'ORD-' || nextval('order_number_seq'),
    session_id text NOT NULL REFERENCES sessions (id),
    subtotal_cents integer NOT NULL,
    shipping_cents integer NOT NULL,
    tax_cents integer NOT NULL,
    total_cents integer NOT NULL,
    cart_hash text NOT NULL,
    status text NOT NULL DEFAULT 'placed' CHECK (status IN ('placed', 'cancelled', 'return_requested')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS orders_session_id_idx ON orders (session_id);

CREATE TABLE IF NOT EXISTS order_lines (
    order_id text NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id text NOT NULL REFERENCES products (id),
    name text NOT NULL,
    category text NOT NULL,
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price_cents integer NOT NULL,
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE IF NOT EXISTS llm_usage (
    day date PRIMARY KEY,
    calls integer NOT NULL DEFAULT 0
);
