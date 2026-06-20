import json
import pandas as pd
import numpy as np


class LearningFailureDetector:
    def __init__(self, dataframe):
        self.df = dataframe.copy()
        self.learning_failures = []
        self.learning_failure_summary = {}

    def detect_failures(self, cv_threshold=0.5, min_events=2):
        for junction in self.df['junction'].unique():
            junction_data = self.df[self.df['junction'] == junction]

            for cluster_id in junction_data['cluster_id'].unique():
                cluster_junction_data = junction_data[junction_data['cluster_id'] == cluster_id]

                if len(cluster_junction_data) < min_events:
                    continue

                recovery_times = cluster_junction_data['recovery_hours'].values
                recovery_times = recovery_times[recovery_times > 0]

                if len(recovery_times) < min_events:
                    continue

                mean_recovery = np.mean(recovery_times)
                std_recovery = np.std(recovery_times)

                if mean_recovery == 0:
                    continue

                cv = std_recovery / mean_recovery

                if cv > cv_threshold:
                    failure = {
                        'junction_name': junction,
                        'cluster_id': int(cluster_id),
                        'event_count': len(cluster_junction_data),
                        'avg_recovery_hours': float(mean_recovery),
                        'std_recovery_hours': float(std_recovery),
                        'coefficient_of_variation': float(cv),
                        'event_type': cluster_junction_data['event_type'].mode()[0],
                        'recovery_times': [float(t) for t in recovery_times],
                        'severity': 'Critical' if cv > 1.0 else 'High',
                    }
                    self.learning_failures.append(failure)

        print(f"Detected {len(self.learning_failures)} learning failure points")

    def rank_failures(self):
        self.learning_failures = sorted(
            self.learning_failures,
            key=lambda x: x['coefficient_of_variation'],
            reverse=True
        )

    def get_summary(self):
        summary = {}
        for failure in self.learning_failures:
            junction = failure['junction_name']
            if junction not in summary:
                summary[junction] = {
                    'junction_name': junction,
                    'total_failure_points': 0,
                    'critical_count': 0,
                    'failure_details': [],
                }
            summary[junction]['total_failure_points'] += 1
            if failure['severity'] == 'Critical':
                summary[junction]['critical_count'] += 1
            summary[junction]['failure_details'].append({
                'cluster_id': failure['cluster_id'],
                'event_type': failure['event_type'],
                'cv': failure['coefficient_of_variation'],
            })

        self.learning_failure_summary = summary
        print(f"Learning failure summary: {len(summary)} junctions with institutional gaps")

    def save_failures(self, output_path):
        with open(output_path, 'w') as f:
            json.dump({
                'failures': self.learning_failures,
                'summary': self.learning_failure_summary,
            }, f, indent=2, default=str)
        print(f"Saved learning failures to {output_path}")

    def get_top_failure_junctions(self, top_n=10):
        summary_list = sorted(
            self.learning_failure_summary.values(),
            key=lambda x: x['critical_count'],
            reverse=True
        )
        return summary_list[:top_n]

    def get_failures(self):
        return self.learning_failures

    def get_summary_data(self):
        return self.learning_failure_summary


if __name__ == '__main__':
    print("=== Loading Clustered Data ===")
    df = pd.read_parquet('data/processed/events_clustered.parquet')

    print("\n=== Detecting Learning Failures ===")
    detector = LearningFailureDetector(df)
    detector.detect_failures(cv_threshold=0.5, min_events=2)
    detector.rank_failures()
    detector.get_summary()

    print("\n=== Top Learning Failure Junctions ===")
    for junction_info in detector.get_top_failure_junctions(top_n=10):
        print(f"{junction_info['junction_name']}: "
              f"{junction_info['total_failure_points']} failure points, "
              f"{junction_info['critical_count']} critical")

    print("\n=== Sample Learning Failures (Top 10) ===")
    for failure in detector.get_failures()[:10]:
        print(f"  {failure['junction_name']} (Cluster {failure['cluster_id']}): "
              f"CV={failure['coefficient_of_variation']:.2f}, "
              f"recovery={failure['recovery_times']}")

    print("\n=== Saving Failures ===")
    detector.save_failures('results/learning_failures.json')
