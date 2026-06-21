import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class RecoveryAuditor:
    """
    Audits recovery time calculations and detects issues:
    - Extreme outliers that distort means
    - Administrative closure durations
    - Data quality problems
    """

    def __init__(self, dataframe):
        self.df = dataframe.copy()
        self.audit_report = {}
        self.outlier_stats = {}

    def compute_robust_recovery(self, recovery_hours: np.ndarray,
                                p_lower: float = 0.25, p_upper: float = 0.75,
                                outlier_threshold: float = 3.0) -> Dict:
        """
        Compute robust recovery statistics resistant to outliers.

        Uses IQR-based outlier detection:
        - Records > Q3 + (outlier_threshold × IQR) are flagged as outliers
        - Returns both raw and outlier-filtered statistics
        - Flags if mean >> median (sign of outliers)
        """
        if len(recovery_hours) == 0:
            return {
                'count': 0,
                'nonzero_count': 0,
                'mean': 0.0,
                'median': 0.0,
                'std': 0.0,
                'p25': 0.0,
                'p75': 0.0,
                'iqr': 0.0,
                'min': 0.0,
                'max': 0.0,
                'has_outliers': False,
                'outlier_count': 0,
                'outlier_indices': [],
                'mean_vs_median_ratio': 1.0,
                'confidence_note': 'No data'
            }

        recovery_nonzero = recovery_hours[recovery_hours > 0]

        if len(recovery_nonzero) == 0:
            return {
                'count': len(recovery_hours),
                'nonzero_count': 0,
                'mean': 0.0,
                'median': 0.0,
                'std': 0.0,
                'p25': 0.0,
                'p75': 0.0,
                'iqr': 0.0,
                'min': 0.0,
                'max': 0.0,
                'has_outliers': False,
                'outlier_count': 0,
                'outlier_indices': [],
                'mean_vs_median_ratio': 1.0,
                'confidence_note': 'All recovery times are zero'
            }

        # Compute IQR-based outlier bounds
        q25 = np.percentile(recovery_nonzero, 25)
        q75 = np.percentile(recovery_nonzero, 75)
        iqr = q75 - q25

        if iqr == 0:
            iqr = 1  # Avoid division by zero

        lower_bound = q25 - (outlier_threshold * iqr)
        upper_bound = q75 + (outlier_threshold * iqr)

        # Identify outliers
        outlier_mask = (recovery_nonzero > upper_bound)
        outlier_indices = np.where(recovery_hours > upper_bound)[0].tolist()
        outlier_count = np.sum(outlier_mask)

        # Compute statistics
        mean_all = float(np.mean(recovery_nonzero))
        median_all = float(np.median(recovery_nonzero))
        std_all = float(np.std(recovery_nonzero))

        # Robust statistics (excluding outliers)
        recovery_robust = recovery_nonzero[~outlier_mask]
        if len(recovery_robust) > 0:
            mean_robust = float(np.mean(recovery_robust))
            median_robust = float(np.median(recovery_robust))
            std_robust = float(np.std(recovery_robust))
        else:
            mean_robust = mean_all
            median_robust = median_all
            std_robust = std_all

        # Assess data quality
        mean_median_ratio = mean_all / median_all if median_all > 0 else 1.0
        outlier_pct = 100.0 * outlier_count / len(recovery_nonzero)

        if mean_median_ratio > 5.0:
            confidence_note = f"⚠️ Extreme mean/median divergence ({mean_median_ratio:.1f}x) - likely administrative durations"
        elif outlier_pct > 10:
            confidence_note = f"⚠️ {outlier_pct:.1f}% outliers detected - median more reliable than mean"
        elif outlier_count > 0:
            confidence_note = f"~ {outlier_count} outliers detected - use caution with mean"
        else:
            confidence_note = "✓ Data appears clean"

        return {
            'count': len(recovery_hours),
            'nonzero_count': len(recovery_nonzero),
            'zero_count': len(recovery_hours) - len(recovery_nonzero),
            'mean': mean_all,
            'median': median_all,
            'std': std_all,
            'mean_robust': mean_robust,
            'median_robust': median_robust,
            'std_robust': std_robust,
            'p25': float(q25),
            'p75': float(q75),
            'iqr': float(iqr),
            'min': float(np.min(recovery_nonzero)),
            'max': float(np.max(recovery_nonzero)),
            'p99': float(np.percentile(recovery_nonzero, 99)),
            'has_outliers': outlier_count > 0,
            'outlier_count': int(outlier_count),
            'outlier_pct': float(outlier_pct),
            'outlier_indices': outlier_indices,
            'outlier_threshold_hours': float(upper_bound),
            'mean_vs_median_ratio': float(mean_median_ratio),
            'confidence_note': confidence_note,
        }

    def audit_clusters(self):
        """Audit recovery times for each cluster."""
        for cluster_id in sorted(self.df['cluster_id'].unique()):
            cluster_data = self.df[self.df['cluster_id'] == cluster_id]
            recovery_hours = cluster_data['recovery_hours'].values

            audit = self.compute_robust_recovery(recovery_hours)
            self.audit_report[int(cluster_id)] = audit

        return self.audit_report

    def audit_junctions(self):
        """Audit recovery times for each junction."""
        audit_by_junction = {}
        for junction in self.df['junction'].unique():
            junction_data = self.df[self.df['junction'] == junction]
            recovery_hours = junction_data['recovery_hours'].values

            audit = self.compute_robust_recovery(recovery_hours)
            audit_by_junction[junction] = audit

        return audit_by_junction

    def generate_report(self) -> Dict:
        """Generate comprehensive audit report."""
        cluster_audits = self.audit_clusters()
        junction_audits = self.audit_junctions()

        # Identify problematic clusters
        problematic_clusters = []
        for cluster_id, audit in cluster_audits.items():
            if audit['has_outliers'] or audit['mean_vs_median_ratio'] > 2.0:
                problematic_clusters.append({
                    'cluster_id': cluster_id,
                    'mean': audit['mean'],
                    'median': audit['median'],
                    'outlier_count': audit['outlier_count'],
                    'outlier_pct': audit['outlier_pct'],
                    'mean_vs_median_ratio': audit['mean_vs_median_ratio'],
                    'confidence_note': audit['confidence_note']
                })

        # Identify Unknown_Junction
        unknown_audit = junction_audits.get('Unknown_Junction', {})
        unknown_pct = 100.0 * len(self.df[self.df['junction'] == 'Unknown_Junction']) / len(self.df)

        return {
            'total_records': len(self.df),
            'total_clusters': len(cluster_audits),
            'total_junctions': len(junction_audits),
            'unknown_junction_pct': float(unknown_pct),
            'unknown_junction_audit': unknown_audit,
            'problematic_clusters': sorted(
                problematic_clusters,
                key=lambda x: x['outlier_pct'],
                reverse=True
            ),
            'cluster_audits': cluster_audits,
            'junction_audits': junction_audits,
        }

    def save_audit(self, output_path: str):
        """Save audit report to file."""
        report = self.generate_report()
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Saved audit report to {output_path}")

    def print_summary(self):
        """Print audit summary to console."""
        report = self.generate_report()

        print("\n" + "="*70)
        print("RECOVERY TIME AUDIT SUMMARY")
        print("="*70)

        print(f"\nDataset: {report['total_records']} records, "
              f"{report['total_clusters']} clusters, "
              f"{report['total_junctions']} junctions")

        print(f"\nUnknown_Junction Contamination:")
        print(f"  - {report['unknown_junction_pct']:.1f}% of all records ({report['unknown_junction_audit'].get('nonzero_count', 0)} nonzero)")
        print(f"  - Mean: {report['unknown_junction_audit'].get('mean', 0):.1f}h, "
              f"Median: {report['unknown_junction_audit'].get('median', 0):.1f}h")
        print(f"  - {report['unknown_junction_audit'].get('confidence_note', '')}")

        print(f"\nProblematic Clusters ({len(report['problematic_clusters'])}):")
        for prob in report['problematic_clusters'][:5]:
            print(f"  Cluster {prob['cluster_id']}: "
                  f"mean={prob['mean']:.1f}h, median={prob['median']:.1f}h, "
                  f"outliers={prob['outlier_count']} ({prob['outlier_pct']:.1f}%)")
            print(f"    {prob['confidence_note']}")


if __name__ == '__main__':
    df = pd.read_parquet('data/processed/events_clustered.parquet')
    auditor = RecoveryAuditor(df)
    auditor.print_summary()
    auditor.save_audit('results/recovery_audit.json')
