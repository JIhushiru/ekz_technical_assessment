PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS vendors (
  vendor_id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS brands (
  brand_id INTEGER PRIMARY KEY,
  vendor_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
);

CREATE TABLE IF NOT EXISTS categories (
  category_id INTEGER PRIMARY KEY,
  vendor_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
);

CREATE TABLE IF NOT EXISTS shipping_tiers (
  shipping_tier_id INTEGER PRIMARY KEY,
  vendor_id INTEGER NOT NULL,
  name TEXT,
  shipping_cost REAL NOT NULL DEFAULT 0,
  FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
);

CREATE TABLE IF NOT EXISTS products (
  sku TEXT PRIMARY KEY,
  vendor_id INTEGER NOT NULL,
  name TEXT,
  cost REAL NOT NULL,
  brand_id INTEGER,
  category_id INTEGER,
  shipping_tier_id INTEGER,
  FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
  FOREIGN KEY (brand_id) REFERENCES brands(brand_id),
  FOREIGN KEY (category_id) REFERENCES categories(category_id),
  FOREIGN KEY (shipping_tier_id) REFERENCES shipping_tiers(shipping_tier_id)
);

CREATE TABLE IF NOT EXISTS repriced_products (
  sku TEXT PRIMARY KEY,
  computed_price REAL NOT NULL,
  target_margin_used REAL NOT NULL,
  total_cost REAL NOT NULL,
  vendor_extra_cost_applied REAL NOT NULL,
  rule_source TEXT NOT NULL,
  computed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_vendor ON products(vendor_id);
