import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select, func
from models import UsageHistory, Segment, CustomerSegmentMap
import numpy as np

def aggregate_features(session):
    stmt = select(
        UsageHistory.customer_id,
        func.avg(UsageHistory.data_mb).label('avg_data_mb'),
        func.avg(UsageHistory.call_minutes).label('avg_call_mins'),
        func.avg(UsageHistory.sms_count).label('avg_sms'),
        func.avg(UsageHistory.app_usage_score).label('avg_app_usage'),
    ).group_by(UsageHistory.customer_id)
    rows = session.execute(stmt).all()
    if not rows:
        return pd.DataFrame(columns=['customer_id','avg_data_mb','avg_call_mins','avg_sms','avg_app_usage'])
    df = pd.DataFrame(rows, columns=['customer_id','avg_data_mb','avg_call_mins','avg_sms','avg_app_usage'])
    df = df.fillna(0)
    return df

def run_segmentation(session, k=3, clear_previous=False):
    df = aggregate_features(session)
    if df.empty:
        return {'status':'no_data'}
    X = df[['avg_data_mb','avg_call_mins','avg_sms','avg_app_usage']].values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    km = KMeans(n_clusters=k, random_state=0, n_init='auto')
    labels = km.fit_predict(Xs)
    df['label'] = labels
    # ensure segment records
    label_to_seg = {}
    for label in sorted(df['label'].unique()):
        name = f'Auto-Segment-{label}'
        seg = session.query(Segment).filter_by(name=name).first()
        if not seg:
            seg = Segment(name=name, description='Auto created by ML pipeline')
            session.add(seg)
            session.flush()
        label_to_seg[label] = seg.id
    # optionally clear previous mappings
    if clear_previous:
        session.query(CustomerSegmentMap).delete()
        session.flush()
    # insert mappings
    for _, row in df.iterrows():
        csm = CustomerSegmentMap(customer_id=int(row['customer_id']), segment_id=label_to_seg[int(row['label'])],
                                 assigned_by='ml_pipeline', method='ml')
        session.add(csm)
    session.commit()
    counts = df['label'].value_counts().to_dict()
    return {'status':'ok','assigned': int(len(df)), 'clusters': counts}
