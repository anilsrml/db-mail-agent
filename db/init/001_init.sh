#!/usr/bin/env bash
set -euo pipefail

# Salt-okunur kullanıcının parolası kaynak koda gömülmez; Docker ortamından gelir.
psql --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=db_name="$POSTGRES_DB" \
  --set=reader_password="$POSTGRES_READER_PASSWORD" <<-'EOSQL'
    CREATE TABLE products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0)
    );

    INSERT INTO products (id, name, stock_quantity) VALUES
        ('P-1001', 'Kablosuz Kulaklık', 100),
        ('P-1002', 'Mekanik Klavye', 0);

    CREATE USER stock_reader WITH PASSWORD :'reader_password';
    GRANT CONNECT ON DATABASE :"db_name" TO stock_reader;
    GRANT USAGE ON SCHEMA public TO stock_reader;
    GRANT SELECT ON TABLE products TO stock_reader;
EOSQL
