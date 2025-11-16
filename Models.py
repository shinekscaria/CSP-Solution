
---

## `models.py`
```python
# models.py
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, DateTime, Boolean, Date, Float, ForeignKey
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    msisdn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200))
    dob: Mapped[Date] = mapped_column(Date, nullable=True)
    location: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    profile = relationship("CustomerProfile", uselist=False, back_populates="customer")
    usage = relationship("UsageHistory", back_populates="customer")

class CustomerProfile(Base):
    __tablename__ = "customer_profile"
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), primary_key=True)
    gender: Mapped[str] = mapped_column(String(20))
    hobby: Mapped[str] = mapped_column(String(200))
    income_bracket: Mapped[str] = mapped_column(String(50))
    customer = relationship("Customer", back_populates="profile")

class UsageHistory(Base):
    __tablename__ = "usage_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"))
    date: Mapped[Date] = mapped_column(Date)
    data_mb: Mapped[int] = mapped_column(Integer, default=0)
    call_minutes: Mapped[int] = mapped_column(Integer, default=0)
    sms_count: Mapped[int] = mapped_column(Integer, default=0)
    app_usage_score: Mapped[float] = mapped_column(Float, default=0.0)
    customer = relationship("Customer", back_populates="usage")

class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    # eligibility_simple: small key=val like "income_bracket=high" or "min_avg_data_mb=3000"
    eligibility_simple: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Segment(Base):
    __tablename__ = "segments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class CustomerSegmentMap(Base):
    __tablename__ = "customer_segment_map"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"))
    segment_id: Mapped[int] = mapped_column(Integer, ForeignKey("segments.id"))
    assigned_by: Mapped[str] = mapped_column(String(100))
    assigned_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    method: Mapped[str] = mapped_column(String(20))

class OfferAssignment(Base):
    __tablename__ = "offer_assignment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"))
    offer_id: Mapped[int] = mapped_column(Integer, ForeignKey("offers.id"))
    assigned_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    assigned_by: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default='assigned')
