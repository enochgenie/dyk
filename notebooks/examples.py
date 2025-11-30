"""
Example Usage Script
Demonstrates both pure LLM and evidence-based generation methods.
"""
import os
import json
from dotenv import load_dotenv
from cohort_generator import CohortGenerator
from insight_generator import InsightGenerator
from validator import InsightValidator, QualityScorer

# Load environment variables from .env file
load_dotenv()


def example_1_quick_test():
    """Example 1: Quick test with a single cohort, both methods."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Quick Test - Single Cohort, Both Methods")
    print("="*80)
    
    # Initialize
    generator = InsightGenerator()
    validator = InsightValidator()
    
    # Define test cohort
    cohort = {
        'cohort_id': 'test_001',
        'cohort_params': {
            'age_group': '40-49',
            'gender': 'male',
            'smoking_status': 'smoker'
        },
        'description': '40-49 years old, male, smoker'
    }
    
    # Method 1: Pure LLM
    print("\n[Pure LLM Method]")
    print("Generating insight using LLM knowledge only...")
    pure_insight = generator.generate_pure_llm(
        cohort_spec=cohort,
        template_type="risk_amplification"
    )
    
    if pure_insight:
        print("\n✓ Generated!")
        print(f"Hook: {pure_insight['hook']}")
        print(f"Source: {pure_insight.get('source_name', 'N/A')}")
        
        # Validate
        validation = validator.validate_insight(pure_insight)
        print(f"Validation Score: {validation['overall_score']}/100")
    
    # Method 2: Evidence-Based
    print("\n[Evidence-Based Method]")
    print("Retrieving evidence from PubMed and generating insight...")
    evidence_insight = generator.generate_evidence_based(
        cohort_spec=cohort,
        template_type="risk_amplification"
    )
    
    if evidence_insight:
        print("\n✓ Generated!")
        print(f"Hook: {evidence_insight['hook']}")
        print(f"Source: {evidence_insight.get('source_name', 'N/A')}")
        print(f"Evidence Sources: {len(evidence_insight.get('evidence_sources', []))}")
        
        # Validate
        validation = validator.validate_insight(evidence_insight)
        print(f"Validation Score: {validation['overall_score']}/100")
    
    # Compare
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    print(f"Pure LLM Source: {pure_insight.get('source_name', 'N/A')}")
    print(f"Evidence-Based Sources: {len(evidence_insight.get('evidence_sources', []))} PubMed articles")


def example_2_multiple_templates():
    """Example 2: Generate multiple insight types for one cohort."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Multiple Template Types")
    print("="*80)
    
    generator = InsightGenerator()
    
    cohort = {
        'cohort_id': 'test_002',
        'cohort_params': {
            'age_group': '30-39',
            'gender': 'female',
            'physical_activity': 'sedentary'
        },
        'description': '30-39 years old, female, sedentary'
    }
    
    templates = [
        "risk_amplification",
        "protective_factors", 
        "behavior_change",
        "early_detection"
    ]
    
    insights = []
    for template in templates:
        print(f"\nGenerating: {template}")
        insight = generator.generate_pure_llm(
            cohort_spec=cohort,
            template_type=template
        )
        
        if insight:
            insights.append(insight)
            print(f"✓ {insight['hook'][:80]}...")
    
    print(f"\nGenerated {len(insights)} insights for this cohort")
    
    # Save to file
    with open('example_2_output.json', 'w') as f:
        json.dump(insights, f, indent=2)
    print("✓ Saved to example_2_output.json")


def example_3_cohort_coverage():
    """Example 3: Generate insights for multiple priority cohorts."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Multiple Cohorts Coverage")
    print("="*80)
    
    # Generate cohorts
    cohort_gen = CohortGenerator()
    cohorts = cohort_gen.generate_priority_cohorts()[:5]  # Top 5 priority
    
    print(f"Selected {len(cohorts)} priority cohorts:")
    for cohort in cohorts:
        print(f"  - {cohort['description']} (priority: {cohort['priority_level']})")
    
    # Generate insights
    generator = InsightGenerator()
    all_insights = []
    
    for cohort in cohorts:
        print(f"\nGenerating for: {cohort['description']}")
        
        insight = generator.generate_pure_llm(
            cohort_spec=cohort,
            template_type="risk_amplification"
        )
        
        if insight:
            all_insights.append(insight)
            print(f"✓ {insight['hook'][:80]}...")
    
    print(f"\n✓ Generated {len(all_insights)} insights across {len(cohorts)} cohorts")
    
    # Save
    with open('example_3_output.json', 'w') as f:
        json.dump(all_insights, f, indent=2)
    print("✓ Saved to example_3_output.json")


def example_4_validation_demo():
    """Example 4: Demonstrate validation capabilities."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Validation & Quality Scoring")
    print("="*80)
    
    validator = InsightValidator()
    scorer = QualityScorer()
    
    # Create sample insights (one good, one problematic)
    insights = [
        {
            'cohort_id': 'test_good',
            'cohort_params': {'age_group': '40-49', 'gender': 'male'},
            'hook': 'Did you know that men in their 40s have 2x higher risk of heart disease?',
            'explanation': 'Studies show that cardiovascular risk increases significantly for men in their 40s due to lifestyle factors and metabolic changes. Regular screening can detect issues early.',
            'action': 'Schedule an annual heart health checkup with your doctor.',
            'source_name': 'American Heart Association',
            'source_url': 'https://www.heart.org/',
            'health_domain': 'cardiovascular'
        },
        {
            'cohort_id': 'test_problematic',
            'cohort_params': {'age_group': '30-39', 'gender': 'female'},
            'hook': 'Health is important!',  # Poor hook
            'explanation': 'You might want to be healthy.',  # Vague
            'action': 'Do something healthy.',  # Not specific
            'source_name': '',  # Missing source
            'source_url': '',
            'health_domain': 'general'
        }
    ]
    
    print("\nValidating insights...")
    for insight in insights:
        print(f"\n{'='*60}")
        print(f"Cohort: {insight['cohort_id']}")
        print(f"Hook: {insight['hook']}")
        
        # Validate
        validation = validator.validate_insight(insight)
        print(f"\nValidation Score: {validation['overall_score']}/100")
        print(f"Valid: {validation['overall_valid']}")
        
        if validation['issues']:
            print(f"Issues: {len(validation['issues'])}")
            for issue in validation['issues'][:3]:
                print(f"  - {issue}")
        
        if validation['warnings']:
            print(f"Warnings: {len(validation['warnings'])}")
            for warning in validation['warnings'][:3]:
                print(f"  - {warning}")
        
        # Quality score
        quality = scorer.calculate_engagement_score(insight)
        print(f"Quality Score: {quality}/100")


def example_5_batch_with_filtering():
    """Example 5: Batch generation with validation filtering."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Batch Generation with Filtering")
    print("="*80)
    
    # Setup
    cohort_gen = CohortGenerator()
    generator = InsightGenerator()
    validator = InsightValidator()
    
    # Get 3 cohorts
    cohorts = cohort_gen.generate_priority_cohorts()[:3]
    
    # Generate 2 insights per cohort
    print(f"Generating insights for {len(cohorts)} cohorts...")
    all_insights = []
    
    for cohort in cohorts:
        print(f"\nCohort: {cohort['description']}")
        
        for i in range(2):
            template = ["risk_amplification", "behavior_change"][i]
            insight = generator.generate_pure_llm(cohort, template_type=template)
            
            if insight:
                all_insights.append(insight)
                print(f"  ✓ Generated ({template})")
    
    print(f"\n✓ Generated {len(all_insights)} total insights")
    
    # Validate all
    print("\nValidating...")
    validation_results = validator.validate_batch(all_insights)
    
    print(f"Valid: {validation_results['valid_insights']}/{validation_results['total_insights']}")
    print(f"Average Score: {validation_results['average_score']}/100")
    
    # Filter to only valid, high-quality insights
    filtered_insights = [
        ins for ins, val in zip(all_insights, validation_results['results'])
        if val['overall_valid'] and val['overall_score'] >= 70
    ]
    
    print(f"\nAfter filtering (score ≥ 70): {len(filtered_insights)} insights")
    
    # Check for duplicates
    duplicates = validator.check_duplicates(filtered_insights)
    if duplicates:
        print(f"Found {len(duplicates)} duplicate pairs")
    else:
        print("No duplicates found")
    
    # Save final
    with open('example_5_output.json', 'w') as f:
        json.dump(filtered_insights, f, indent=2)
    print("\n✓ Saved filtered insights to example_5_output.json")


def example_6_evidence_comparison():
    """Example 6: Compare evidence quality between methods."""
    print("\n" + "="*80)
    print("EXAMPLE 6: Evidence Quality Comparison")
    print("="*80)
    
    generator = InsightGenerator()
    
    cohort = {
        'cohort_id': 'test_006',
        'cohort_params': {
            'age_group': '50-59',
            'gender': 'female',
            'chronic_conditions': 'diabetes'
        },
        'description': '50-59 years old, female, diabetes'
    }
    
    print("Generating same insight with both methods...\n")
    
    # Pure LLM
    print("[Method 1: Pure LLM]")
    pure_insight = generator.generate_pure_llm(cohort)
    if pure_insight:
        print(f"Source: {pure_insight.get('source_name', 'N/A')}")
        print(f"Confidence: {pure_insight.get('confidence', 'N/A')}")
        print(f"Numeric Claim: {pure_insight.get('numeric_claim', 'N/A')}")
    
    # Evidence-based
    print("\n[Method 2: Evidence-Based]")
    evidence_insight = generator.generate_evidence_based(cohort)
    if evidence_insight:
        print(f"Source: {evidence_insight.get('source_name', 'N/A')}")
        print(f"PMID: {evidence_insight.get('source_pmid', 'N/A')}")
        print(f"Evidence Sources: {len(evidence_insight.get('evidence_sources', []))}")
        
        # Show evidence sources
        if evidence_insight.get('evidence_sources'):
            print("\nEvidence Sources Used:")
            for i, source in enumerate(evidence_insight['evidence_sources'][:3], 1):
                print(f"  {i}. {source.get('title', 'N/A')[:80]}...")
                print(f"     {source.get('journal', 'N/A')} ({source.get('year', 'N/A')})")
    
    # Compare
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    print("Pure LLM:")
    print("  ✓ Faster generation")
    print("  ✓ Lower cost")
    print("  ⚠ Generic sources")
    print("\nEvidence-Based:")
    print("  ✓ Specific PubMed citations")
    print("  ✓ Recent research")
    print("  ✓ Lower hallucination risk")
    print("  ⚠ Slower, higher cost")


def main():
    """Run all examples."""
    import sys
    
    print("\n" + "="*80)
    print("DYK INSIGHT GENERATION - EXAMPLE USAGE")
    print("="*80)
    
    examples = {
        '1': ('Quick Test (Single Cohort, Both Methods)', example_1_quick_test),
        '2': ('Multiple Template Types', example_2_multiple_templates),
        '3': ('Multiple Cohorts Coverage', example_3_cohort_coverage),
        '4': ('Validation & Quality Scoring', example_4_validation_demo),
        '5': ('Batch Generation with Filtering', example_5_batch_with_filtering),
        '6': ('Evidence Quality Comparison', example_6_evidence_comparison),
    }
    
    print("\nAvailable Examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  all. Run all examples")
    print("  q. Quit")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nSelect example (1-6, all, or q): ").strip()
    
    if choice == 'q':
        return
    
    if choice == 'all':
        for _, func in examples.values():
            try:
                func()
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
    elif choice in examples:
        try:
            examples[choice][1]()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Invalid choice")
    
    print("\n" + "="*80)
    print("Examples complete!")
    print("="*80)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv('OPENROUTER_API_KEY'):
        print("\n⚠ WARNING: OPENROUTER_API_KEY not set!")
        print("Set it with: export OPENROUTER_API_KEY='your-key'")
        print("Or add to .env file")
        print("\nContinuing anyway for demonstration...")
    
    main()
