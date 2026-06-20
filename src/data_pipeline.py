import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json

class DataPipeline:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = None
        self.encoders = {}

    def load_data(self):
        self.df = pd.read_csv(self.csv_path)
        print(f"Loaded {len(self.df)} events")
        return self.df

    def clean_data(self):
        df = self.df.copy()

        # Convert timestamps with mixed format handling
        df['start_datetime'] = pd.to_datetime(df['start_datetime'], utc=True, format='mixed', errors='coerce')
        df['resolved_datetime'] = pd.to_datetime(df['resolved_datetime'], utc=True, format='mixed', errors='coerce')
        df['end_datetime'] = pd.to_datetime(df['end_datetime'], utc=True, format='mixed', errors='coerce')

        # Handle missing resolved_datetime: use end_datetime if available, else start_datetime
        df['resolved_datetime'] = df['resolved_datetime'].fillna(df['end_datetime'])
        df['resolved_datetime'] = df['resolved_datetime'].fillna(df['start_datetime'])

        # Drop rows with missing critical fields
        critical_fields = ['id', 'event_type', 'priority', 'corridor', 'start_datetime', 'zone']
        df = df.dropna(subset=critical_fields)

        # Fill junction with 'Unknown' if missing
        df['junction'] = df['junction'].fillna('Unknown_Junction')

        print(f"Cleaned to {len(df)} events after removing nulls")
        self.df = df
        return self.df

    def engineer_features(self):
        df = self.df.copy()

        # Calculate recovery time in hours
        df['recovery_hours'] = (df['resolved_datetime'] - df['start_datetime']).dt.total_seconds() / 3600
        df['recovery_hours'] = df['recovery_hours'].clip(lower=0).fillna(0)

        # Extract temporal features
        df['hour_of_day'] = df['start_datetime'].dt.hour
        df['day_of_week'] = df['start_datetime'].dt.dayofweek
        df['date'] = df['start_datetime'].dt.date

        # Handle empty/null values in categorical fields
        df['event_type'] = df['event_type'].fillna('unknown')
        df['event_cause'] = df['event_cause'].fillna('unknown')
        df['corridor'] = df['corridor'].fillna('Non-corridor')
        df['zone'] = df['zone'].fillna('Unknown_Zone')

        # Encode categorical variables (one-hot for clustering)
        self.encoders['event_type'] = {v: i for i, v in enumerate(df['event_type'].unique())}
        self.encoders['corridor'] = {v: i for i, v in enumerate(df['corridor'].unique())}
        self.encoders['zone'] = {v: i for i, v in enumerate(df['zone'].unique())}
        self.encoders['priority'] = {'Low': 0, 'High': 1}

        df['event_type_encoded'] = df['event_type'].map(self.encoders['event_type'])
        df['corridor_encoded'] = df['corridor'].map(self.encoders['corridor'])
        df['zone_encoded'] = df['zone'].map(self.encoders['zone'])
        df['priority_encoded'] = df['priority'].map(self.encoders['priority']).fillna(0).astype(int)

        print(f"Engineered features: {df.shape[1]} columns")
        self.df = df
        return self.df

    def get_clustering_features(self):
        feature_cols = ['event_type_encoded', 'priority_encoded', 'corridor_encoded', 'zone_encoded', 'hour_of_day']
        return self.df[feature_cols].fillna(0).values

    def save_processed(self, output_path):
        self.df.to_parquet(output_path)
        print(f"Saved processed data to {output_path}")

    def save_encoders(self, output_path):
        with open(output_path, 'w') as f:
            json.dump(self.encoders, f)
        print(f"Saved encoders to {output_path}")

    def get_dataframe(self):
        return self.df


if __name__ == '__main__':
    pipeline = DataPipeline('data/raw/events_raw.csv')
    pipeline.load_data()
    pipeline.clean_data()
    pipeline.engineer_features()
    pipeline.save_processed('data/processed/events_cleaned.parquet')
    pipeline.save_encoders('data/processed/encoders.json')
    print(f"\nFinal dataset shape: {pipeline.df.shape}")
    print(f"Junctions: {pipeline.df['junction'].nunique()}")
    print(f"Event types: {pipeline.df['event_type'].nunique()}")
    print(f"Corridors: {pipeline.df['corridor'].nunique()}")
