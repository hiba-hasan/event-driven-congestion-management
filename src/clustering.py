import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score


class EventDNAClustering:
    def __init__(self, dataframe, features_matrix, encoders):
        self.df = dataframe.copy()
        self.features = features_matrix
        self.encoders = encoders
        self.kmeans = None
        self.cluster_labels = None
        self.cluster_profiles = {}
        self.scaler = StandardScaler()

    def find_optimal_k(self, k_range=(3, 10)):
        scaled_features = self.scaler.fit_transform(self.features)
        silhouette_scores = []

        for k in range(k_range[0], k_range[1] + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(scaled_features)
            score = silhouette_score(scaled_features, labels)
            silhouette_scores.append(score)
            print(f"k={k}: silhouette={score:.3f}")

        optimal_k = k_range[0] + np.argmax(silhouette_scores)
        print(f"\nOptimal k={optimal_k} with silhouette score={max(silhouette_scores):.3f}")
        return optimal_k

    def fit(self, k=6):
        scaled_features = self.scaler.fit_transform(self.features)
        self.kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        self.cluster_labels = self.kmeans.fit_predict(scaled_features)
        self.df['cluster_id'] = self.cluster_labels

        print(f"Clustering complete with k={k}")
        print(f"Cluster distribution:\n{pd.Series(self.cluster_labels).value_counts().sort_index()}")

    def generate_profiles(self):
        reverse_encoders = {
            'event_type': {v: k for k, v in self.encoders['event_type'].items()},
            'corridor': {v: k for k, v in self.encoders['corridor'].items()},
            'zone': {v: k for k, v in self.encoders['zone'].items()},
        }

        for cluster_id in sorted(self.df['cluster_id'].unique()):
            cluster_data = self.df[self.df['cluster_id'] == cluster_id]

            profile = {
                'cluster_id': int(cluster_id),
                'event_count': len(cluster_data),
                'dominant_event_type': cluster_data['event_type'].mode()[0] if len(cluster_data) > 0 else 'unknown',
                'dominant_priority': cluster_data['priority'].mode()[0] if len(cluster_data) > 0 else 'Low',
                'dominant_corridor': cluster_data['corridor'].mode()[0] if len(cluster_data) > 0 else 'Non-corridor',
                'dominant_zone': cluster_data['zone'].mode()[0] if len(cluster_data) > 0 else 'Unknown',
                'avg_recovery_hours': float(cluster_data['recovery_hours'].mean()),
                'median_recovery_hours': float(cluster_data['recovery_hours'].median()),
                'affected_junctions': list(cluster_data['junction'].unique()),
                'event_causes': list(cluster_data['event_cause'].value_counts().head(3).index),
            }

            self.cluster_profiles[int(cluster_id)] = profile

        print(f"\nGenerated profiles for {len(self.cluster_profiles)} clusters")

    def save_profiles(self, output_path):
        with open(output_path, 'w') as f:
            json.dump(self.cluster_profiles, f, indent=2, default=str)
        print(f"Saved cluster profiles to {output_path}")

    def save_clustered_data(self, output_path):
        self.df.to_parquet(output_path)
        print(f"Saved clustered data to {output_path}")

    def get_dataframe(self):
        return self.df

    def get_profiles(self):
        return self.cluster_profiles


if __name__ == '__main__':
    # Run data pipeline first
    from data_pipeline import DataPipeline

    print("=== Step 1: Data Pipeline ===")
    pipeline = DataPipeline('data/raw/events_raw.csv')
    pipeline.load_data()
    pipeline.clean_data()
    pipeline.engineer_features()
    df = pipeline.get_dataframe()
    features = pipeline.get_clustering_features()
    encoders = pipeline.encoders

    print("\n=== Step 2: Event DNA Clustering ===")
    clustering = EventDNAClustering(df, features, encoders)
    optimal_k = clustering.find_optimal_k(k_range=(3, 10))
    clustering.fit(k=optimal_k)
    clustering.generate_profiles()

    print("\n=== Saving Outputs ===")
    clustering.save_profiles('results/cluster_profiles.json')
    clustering.save_clustered_data('data/processed/events_clustered.parquet')

    print("\n=== Cluster Profiles ===")
    for cluster_id, profile in clustering.get_profiles().items():
        print(f"Cluster {cluster_id}: {profile['event_count']} events, "
              f"type={profile['dominant_event_type']}, "
              f"avg_recovery={profile['avg_recovery_hours']:.1f}h")
