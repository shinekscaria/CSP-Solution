# scripts/seed.py
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, User, Customer, CustomerProfile, UsageHistory, Offer, Segment
from werkzeug.security import generate_password_hash
import os

DB = os.environ.get('DATABASE_URL', 'sqlite:///csp.db')

def seed():
    engine = create_engine(DB, echo=False, future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # create admin user
        if not session.query(User).filter_by(username='admin').first():
            admin = User(username='admin', password_hash=generate_password_hash('admin123'), role='admin')
            session.add(admin)

        # sample customers
        if session.query(Customer).count() == 0:
            customers = [
                Customer(msisdn='9990000001', name='Alice', location='Chennai'),
                Customer(msisdn='9990000002', name='Bob', location='Bengaluru'),
                Customer(msisdn='9990000003', name='Charlie', location='Hyderabad'),
                Customer(msisdn='9990000004', name='Dave', location='Mumbai'),
                Customer(msisdn='9990000005', name='Eve', location='Delhi'),
            ]
            session.add_all(customers)
            session.flush()
            # profiles
            profiles = [
                CustomerProfile(customer_id=customers[0].id, gender='F', hobby='Streaming', income_bracket='high'),
                CustomerProfile(customer_id=customers[1].id, gender='M', hobby='Gaming', income_bracket='medium'),
                CustomerProfile(customer_id=customers[2].id, gender='M', hobby='Browsing', income_bracket='low'),
                CustomerProfile(customer_id=customers[3].id, gender='M', hobby='Streaming', income_bracket='high'),
                CustomerProfile(customer_id=customers[4].id, gender='F', hobby='Social', income_bracket='low'),
            ]
            session.add_all(profiles)
            session.flush()
            today = datetime.date.today()
            # usage history for last 3 months
            import random
            for cust in customers:
                for m in range(3):
                    d = today - datetime.timedelta(days=30*m)
                    usage = UsageHistory(customer_id=cust.id,
                                         date=d,
                                         data_mb=random.randint(100, 10000),
                                         call_minutes=random.randint(10, 500),
                                         sms_count=random.randint(0, 200),
                                         app_usage_score=round(random.random()*10,2))
                    session.add(usage)

        # sample offers: use simple eligibility string: "min_avg_data_mb=XXXX" or "income_bracket=high"
        if session.query(Offer).count() == 0:
            offers = [
                Offer(code='OFFER_HIGH_PREM', title='Premium Discount 10%', description='10% off premium plan', eligibility_simple='income_bracket=high'),
                Offer(code='OFFER_DATA_BOOST', title='2GB bonus for heavy users', description='2GB extra for 1 month', eligibility_simple='min_avg_data_mb=3000'),
                Offer(code='OFFER_BUDGET', title='Budget Booster', description='1GB extra for budget customers', eligibility_simple='income_bracket=low'),
            ]
            session.add_all(offers)

        # sample segments (optional)
        if session.query(Segment).count() == 0:
            segs = [
                Segment(name='High-Value', description='High lifetime value'),
                Segment(name='Budget', description='Budget-conscious'),
                Segment(name='High-Usage', description='Heavy data users'),
            ]
            session.add_all(segs)

        session.commit()
    print("Seed complete: DB created at csp.db")

if __name__ == "__main__":
    seed()
