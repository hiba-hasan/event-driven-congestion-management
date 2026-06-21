import json
import pandas as pd
import numpy as np


class ResilienceScoring:
    def __init__(self, dataframe):
        self.df = dataframe.copy()
        self.junction_scores = {}
        self.corridor_scores = {}
        self.zone_scores = {}

    def compute_junction_scores(self):
        for junction in self.df['junction'].unique():
            junction_data = self.df[self.df['junction'] == junction]

            recovery_times = junction_data['recovery_hours'].values
            recovery_times = recovery_times[recovery_times > 0]

            if len(recovery_times) == 0:
                recovery_times = np.array([0])

            avg_recovery = float(np.mean(recovery_times))
            median_recovery = float(np.median(recovery_times))
            std_recovery = float(np.std(recovery_times))

            # Use median for resilience scoring to handle outliers
            # Note: Audit shows mean >> median in many clusters, indicating administrative durations
            resilience_score = 1.0 / (1.0 + median_recovery)

            self.junction_scores[junction] = {
                'junction_name': junction,
                'event_count': int(len(junction_data)),
                'avg_recovery_hours': avg_recovery,
                'median_recovery_hours': median_recovery,
                'std_recovery_hours': std_recovery,
                'resilience_score': resilience_score,
                'resilience_category': 'Resilient' if resilience_score >= 0.5 else 'Fragile',
                'primary_zone': junction_data['zone'].mode()[0] if len(junction_data) > 0 else 'Unknown',
                'primary_corridor': junction_data['corridor'].mode()[0] if len(junction_data) > 0 else 'Non-corridor',
                'event_types': list(junction_data['event_type'].unique()),
            }

        print(f"Computed resilience scores for {len(self.junction_scores)} junctions (using median recovery for robustness)")

    def compute_aggregate_scores(self):
        for corridor in self.df['corridor'].unique():
            corridor_data = self.df[self.df['corridor'] == corridor]
            recovery_times = corridor_data['recovery_hours'].values[corridor_data['recovery_hours'].values > 0]

            if len(recovery_times) == 0:
                recovery_times = np.array([0])

            resilience_score = 1.0 / (1.0 + np.mean(recovery_times))
            self.corridor_scores[corridor] = {
                'corridor_name': corridor,
                'event_count': len(corridor_data),
                'avg_recovery_hours': float(np.mean(recovery_times)),
                'resilience_score': resilience_score,
            }

        for zone in self.df['zone'].unique():
            zone_data = self.df[self.df['zone'] == zone]
            recovery_times = zone_data['recovery_hours'].values[zone_data['recovery_hours'].values > 0]

            if len(recovery_times) == 0:
                recovery_times = np.array([0])

            resilience_score = 1.0 / (1.0 + np.mean(recovery_times))
            self.zone_scores[zone] = {
                'zone_name': zone,
                'event_count': len(zone_data),
                'avg_recovery_hours': float(np.mean(recovery_times)),
                'resilience_score': resilience_score,
            }

        print(f"Computed aggregate scores for {len(self.corridor_scores)} corridors, {len(self.zone_scores)} zones")

    def get_fragile_junctions(self, top_n=10):
        sorted_junctions = sorted(
            self.junction_scores.values(),
            key=lambda x: x['resilience_score']
        )
        return sorted_junctions[:top_n]

    def get_resilient_junctions(self, top_n=10):
        sorted_junctions = sorted(
            self.junction_scores.values(),
            key=lambda x: x['resilience_score'],
            reverse=True
        )
        return sorted_junctions[:top_n]

    def save_scores(self, junction_path, corridor_path=None, zone_path=None):
        with open(junction_path, 'w') as f:
            json.dump(self.junction_scores, f, indent=2, default=str)
        print(f"Saved junction scores to {junction_path}")

        if corridor_path:
            with open(corridor_path, 'w') as f:
                json.dump(self.corridor_scores, f, indent=2, default=str)
            print(f"Saved corridor scores to {corridor_path}")

        if zone_path:
            with open(zone_path, 'w') as f:
                json.dump(self.zone_scores, f, indent=2, default=str)
            print(f"Saved zone scores to {zone_path}")

    def get_junction_scores(self):
        return self.junction_scores

    def get_corridor_scores(self):
        return self.corridor_scores

    def get_zone_scores(self):
        return self.zone_scores


if __name__ == '__main__':
    print("=== Loading Clustered Data ===")
    df = pd.read_parquet('data/processed/events_clustered.parquet')

    print("\n=== Computing Resilience Scores ===")
    scoring = ResilienceScoring(df)
    scoring.compute_junction_scores()
    scoring.compute_aggregate_scores()

    print("\n=== Top 10 Most Fragile Junctions ===")
    for junction in scoring.get_fragile_junctions(top_n=10):
        print(f"{junction['junction_name']}: score={junction['resilience_score']:.3f}, "
              f"avg_recovery={junction['avg_recovery_hours']:.1f}h, "
              f"events={junction['event_count']}")

    print("\n=== Top 10 Most Resilient Junctions ===")
    for junction in scoring.get_resilient_junctions(top_n=10):
        print(f"{junction['junction_name']}: score={junction['resilience_score']:.3f}, "
              f"avg_recovery={junction['avg_recovery_hours']:.1f}h, "
              f"events={junction['event_count']}")

    print("\n=== Saving Scores ===")
    scoring.save_scores(
        'results/junction_scores.json',
        'results/corridor_scores.json',
        'results/zone_scores.json'
    )
