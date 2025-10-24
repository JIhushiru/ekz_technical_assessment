from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, func

class Base(DeclarativeBase):
    pass

class Vendor(Base):
    __tablename__ = "vendors"
    vendor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

class Brand(Base):
    __tablename__ = "brands"
    brand_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

class Category(Base):
    __tablename__ = "categories"
    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

class ShippingTier(Base):
    __tablename__ = "shipping_tiers"
    shipping_tier_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    shipping_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

class Product(Base):
    __tablename__ = "products"
    sku: Mapped[str] = mapped_column(String, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.brand_id"), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.category_id"), nullable=True)
    shipping_tier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shipping_tiers.shipping_tier_id"), nullable=True)

class RepricedProduct(Base):
    __tablename__ = "repriced_products"
    sku: Mapped[str] = mapped_column(String, primary_key=True)
    computed_price: Mapped[float] = mapped_column(Float, nullable=False)
    target_margin_used: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    vendor_extra_cost_applied: Mapped[float] = mapped_column(Float, nullable=False)
    rule_source: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp())
