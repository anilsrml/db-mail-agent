-- Bu dosya terminalden tekrar çalıştırılabilir. Aynı ürünler zaten varsa
-- çoğaltmak yerine eğitim senaryosundaki sabit stok değerlerine geri döndürür.
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0)
);

INSERT INTO products (id, name, stock_quantity) VALUES
    ('P-1001', 'Kablosuz Kulaklık', 100),
    ('P-1002', 'Mekanik Klavye', 0)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    stock_quantity = EXCLUDED.stock_quantity;

