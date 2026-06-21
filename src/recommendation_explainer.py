from typing import Dict, List, Tuple


class RecommendationExplainer:
    """
    Generates transparent, auditable recommendations with full breakdowns.
    Each recommendation shows WHY a number was chosen, not just WHAT the number is.
    """

    @staticmethod
    def calculate_police_deployment_with_breakdown(
        recovery_hours: float,
        affected_junctions: int,
        learning_penalty: float,
        has_road_closure: bool = False
    ) -> Dict:
        """
        Calculate police officers needed with full breakdown.

        Formula:
        Base (2) + Recovery Component + Junction Component + Learning Penalty + Closure Bonus
        """
        breakdown = {
            'base': 2,
            'components': {}
        }

        # Component 1: Recovery time (1 officer per ~100 hours)
        recovery_component = recovery_hours / 100.0
        breakdown['components']['recovery_hours'] = {
            'value': recovery_component,
            'factor': recovery_hours,
            'reasoning': f'{recovery_hours:.1f}h recovery ÷ 100h per officer'
        }

        # Component 2: Junction count (1 officer per ~10 junctions)
        junction_component = affected_junctions / 10.0
        breakdown['components']['affected_junctions'] = {
            'value': junction_component,
            'factor': affected_junctions,
            'reasoning': f'{affected_junctions} junctions ÷ 10 per officer'
        }

        # Component 3: Learning penalty (institutional gaps)
        breakdown['components']['learning_penalty'] = {
            'value': learning_penalty,
            'factor': learning_penalty,
            'reasoning': f'Institutional learning failure penalty'
        }

        # Component 4: Road closure bonus
        closure_bonus = 1.0 if has_road_closure else 0.0
        breakdown['components']['road_closure'] = {
            'value': closure_bonus,
            'factor': has_road_closure,
            'reasoning': f'Road closure requires additional coordination'
        }

        total = breakdown['base'] + sum(c['value'] for c in breakdown['components'].values())
        recommended = max(round(total), 2)

        breakdown['total_before_rounding'] = total
        breakdown['recommended'] = recommended
        breakdown['explanation'] = (
            f"{breakdown['base']} (base) + "
            f"{recovery_component:.1f} (recovery) + "
            f"{junction_component:.1f} (junctions) + "
            f"{learning_penalty:.1f} (learning) + "
            f"{closure_bonus:.1f} (closure) = {total:.1f} → {recommended} officers"
        )

        return breakdown

    @staticmethod
    def calculate_barricades_with_breakdown(
        road_closure: str,
        affected_junctions: int,
        recovery_hours: float
    ) -> Dict:
        """
        Calculate barricades needed with full breakdown.

        Rules:
        - Road closure: +2 units
        - >20 affected junctions: +1 unit
        - >300h recovery: +1 unit
        """
        breakdown = {
            'rules_applied': []
        }

        barricades = 0

        if road_closure == "Yes":
            breakdown['rules_applied'].append({
                'rule': 'Road closure',
                'value': 2,
                'applied': True
            })
            barricades += 2
        else:
            breakdown['rules_applied'].append({
                'rule': 'Road closure',
                'value': 0,
                'applied': False
            })

        if affected_junctions > 20:
            breakdown['rules_applied'].append({
                'rule': f'Affected junctions > 20 ({affected_junctions})',
                'value': 1,
                'applied': True
            })
            barricades += 1
        else:
            breakdown['rules_applied'].append({
                'rule': f'Affected junctions > 20 ({affected_junctions})',
                'value': 0,
                'applied': False
            })

        if recovery_hours > 300:
            breakdown['rules_applied'].append({
                'rule': f'Recovery hours > 300 ({recovery_hours:.1f}h)',
                'value': 1,
                'applied': True
            })
            barricades += 1
        else:
            breakdown['rules_applied'].append({
                'rule': f'Recovery hours > 300 ({recovery_hours:.1f}h)',
                'value': 0,
                'applied': False
            })

        breakdown['recommended'] = barricades
        breakdown['explanation'] = (
            f"Road closure: {2 if road_closure == 'Yes' else 0} + "
            f"Junctions: {1 if affected_junctions > 20 else 0} + "
            f"Recovery: {1 if recovery_hours > 300 else 0} = {barricades} units"
        )

        return breakdown

    @staticmethod
    def calculate_coordinator_level_with_breakdown(
        has_critical_failures: bool,
        has_high_failures: bool,
        learning_penalty: float
    ) -> Dict:
        """
        Determine if senior coordinator is needed.

        Rules:
        - Critical learning failures → Senior ⭐
        - High learning failures + penalty ≥ 1 → Senior ⭐
        - Otherwise → Standard
        """
        breakdown = {
            'factors': {}
        }

        breakdown['factors']['critical_failures'] = {
            'present': has_critical_failures,
            'impact': 'Escalates to Senior'
        }
        breakdown['factors']['high_failures'] = {
            'present': has_high_failures,
            'learning_penalty': learning_penalty,
            'impact': 'Escalates to Senior if penalty ≥ 1'
        }

        needs_senior = has_critical_failures or (has_high_failures and learning_penalty >= 1)

        breakdown['recommended'] = 'Senior ⭐' if needs_senior else 'Standard'
        breakdown['explanation'] = (
            f"Senior coordinator needed: " +
            (f"Critical failures detected" if has_critical_failures else
             f"High failures + penalty ({learning_penalty:.1f})" if needs_senior else
             f"No learning gaps")
        )

        return breakdown

    @staticmethod
    def calculate_diversion_with_breakdown(
        primary_corridor: str,
        num_affected_junctions: int
    ) -> Dict:
        """
        Determine diversion strategy.

        Rules:
        - Non-corridor events: Localized management
        - Named corridor + >5 junctions: Full diversion required
        - Otherwise: Partial diversion
        """
        breakdown = {
            'factors': {
                'primary_corridor': primary_corridor,
                'affected_junctions': num_affected_junctions,
            }
        }

        if primary_corridor == "Non-corridor":
            strategy = "Localized"
            explanation = f"Localized event - manage within {num_affected_junctions} affected junctions"
        elif num_affected_junctions > 5:
            strategy = "Full"
            explanation = f"Avoid {primary_corridor} corridor ({num_affected_junctions} junctions affected)"
        else:
            strategy = "Partial"
            explanation = f"Partial diversion on {primary_corridor} corridor ({num_affected_junctions} junctions)"

        breakdown['recommended'] = strategy
        breakdown['explanation'] = explanation

        return breakdown


class ConfidenceExplainer:
    """
    Explains recommendation confidence with transparent factor analysis.
    """

    @staticmethod
    def calculate_confidence_with_breakdown(
        similarity_score: float,
        cluster_event_count: int,
        has_learning_failures: bool,
        unknown_junction_pct: float
    ) -> Dict:
        """
        Calculate recommendation confidence with full factor breakdown.

        Confidence = Similarity Score (normalized) adjusted by:
        - Event count in cluster (more events = more reliable)
        - Learning failures (reduce confidence if severe)
        - Data quality (reduce confidence if contaminated)
        """
        breakdown = {
            'base_score': similarity_score / 100.0,  # Normalize to 0-1
            'factors': {},
            'adjustments': []
        }

        confidence = similarity_score / 100.0

        # Factor 1: Cluster size (event count)
        if cluster_event_count >= 100:
            factor_value = 1.0
            adjustment_text = f"Large cluster ({cluster_event_count} events) - data-rich"
        elif cluster_event_count >= 50:
            factor_value = 0.85
            adjustment_text = f"Medium cluster ({cluster_event_count} events) - reasonable"
        elif cluster_event_count >= 20:
            factor_value = 0.7
            adjustment_text = f"Small cluster ({cluster_event_count} events) - limited samples"
        else:
            factor_value = 0.5
            adjustment_text = f"Tiny cluster ({cluster_event_count} events) - very limited"

        breakdown['factors']['cluster_event_count'] = {
            'value': cluster_event_count,
            'confidence_factor': factor_value,
            'note': adjustment_text
        }

        # Factor 2: Learning failures
        if has_learning_failures:
            learning_factor = 0.8
            breakdown['adjustments'].append({
                'factor': 'learning_failures',
                'multiplier': learning_factor,
                'reasoning': 'Historical inconsistency detected - responses may vary'
            })
            confidence *= learning_factor
        else:
            breakdown['adjustments'].append({
                'factor': 'learning_failures',
                'multiplier': 1.0,
                'reasoning': 'No inconsistency - historical responses reliable'
            })

        # Factor 3: Data quality (Unknown_Junction contamination)
        if unknown_junction_pct > 30:
            data_quality_factor = 0.85
            breakdown['adjustments'].append({
                'factor': 'data_quality',
                'multiplier': data_quality_factor,
                'reasoning': f'Data quality concern: {unknown_junction_pct:.1f}% records lack junction info'
            })
            confidence *= data_quality_factor
        elif unknown_junction_pct > 10:
            data_quality_factor = 0.9
            breakdown['adjustments'].append({
                'factor': 'data_quality',
                'multiplier': data_quality_factor,
                'reasoning': f'Minor data quality issue: {unknown_junction_pct:.1f}% records lack junction info'
            })
            confidence *= data_quality_factor
        else:
            breakdown['adjustments'].append({
                'factor': 'data_quality',
                'multiplier': 1.0,
                'reasoning': f'Data quality acceptable ({unknown_junction_pct:.1f}% unknown)'
            })

        # Clamp to 0-1
        confidence = max(0, min(1, confidence))

        breakdown['final_confidence'] = confidence
        breakdown['confidence_pct'] = int(confidence * 100)
        breakdown['interpretation'] = (
            "High confidence ✓" if confidence >= 0.8 else
            "Medium confidence ~" if confidence >= 0.5 else
            "Low confidence ⚠️"
        )

        breakdown['explanation'] = (
            f"Base: {similarity_score}/100 ({similarity_score/100:.1%}) × "
            f"{factor_value:.0%} (cluster size) × "
            f"{(' × '.join([str(a['multiplier']) for a in breakdown['adjustments']]))} "
            f"(adjustments) = {confidence:.0%}"
        )

        return breakdown


if __name__ == '__main__':
    # Test explainer
    police = RecommendationExplainer.calculate_police_deployment_with_breakdown(
        recovery_hours=347.0,
        affected_junctions=25,
        learning_penalty=3.0,
        has_road_closure=True
    )
    print("\nPolice Deployment Breakdown:")
    print(f"  {police['explanation']}")

    barricades = RecommendationExplainer.calculate_barricades_with_breakdown(
        road_closure="Yes",
        affected_junctions=25,
        recovery_hours=347.0
    )
    print("\nBarricades Breakdown:")
    print(f"  {barricades['explanation']}")

    confidence = ConfidenceExplainer.calculate_confidence_with_breakdown(
        similarity_score=85,
        cluster_event_count=124,
        has_learning_failures=True,
        unknown_junction_pct=36.2
    )
    print("\nConfidence Breakdown:")
    print(f"  {confidence['explanation']}")
    print(f"  Interpretation: {confidence['interpretation']}")
