#!/usr/bin/env python3
"""
End-to-end DYK insight generation workflow.

Steps:
1. Generate cohorts
2. Generate insights via LLM for each cohort and sampled health domain + sampled insight template
3. Validate each insight
4. Evaluate insights for quality (only for those which pass validation)
5. Save results

Metadata is appended throughout the pipeline including:
- Generation model, timestamp
- Validation details
- Evaluation details
"""

import os
import sys
import json
import time
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Import core modules
from src.core.cohort_generator import CohortGenerator
from src.core.insight_generator import InsightGenerator, OpenRouterClient
from src.core.validator import InsightValidator
from src.core.evaluator import InsightEvaluator
from src.services.pubmed_service import EvidenceRetriever, PubMedAPI
from src.prompts.prompt_templates import PromptTemplates
from src.utils.config_loader import ConfigLoader

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


class DYKPipeline:
    """End-to-end DYK insight generation pipeline."""

    def __init__(
        self,
        market: str = "singapore",
        openrouter_api_key: Optional[str] = None,
        pubmed_email: Optional[str] = None,
        pubmed_api_key: Optional[str] = None,
        generation_model: str = "x-ai/grok-4.1-fast",
        evaluation_model: str = "x-ai/grok-4.1-fast",
        generation_temperature: float = 0.7,
        generation_max_tokens: int = 2000,
    ):
        """
        Initialize the pipeline with all necessary components.

        Args:
            market: Target market/region
            openrouter_api_key: OpenRouter API key
            pubmed_email: Email for PubMed API
            pubmed_api_key: PubMed API key (optional)
            model: LLM model to use
            generation_temperature: LLM temperature for generation
            generation_max_tokens: Maximum tokens for LLM generation
        """
        self.market = market
        self.generation_model = generation_model
        self.evaluation_model = evaluation_model
        self.generation_temperature = generation_temperature
        self.generation_max_tokens = generation_max_tokens

        # Load configuration
        print(f"Loading configuration for market: {market}")
        self.config_loader = ConfigLoader(market=market)

        # Initialize components
        print("Initializing pipeline components...")

        # 1. Cohort Generator
        self.cohort_generator = CohortGenerator(market=market)

        # 2. LLM Clients
        api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY environment variable."
            )
        self.gen_llm = OpenRouterClient(model=generation_model, api_key=api_key)
        self.eval_llm = OpenRouterClient(model=evaluation_model, api_key=api_key)

        # 3. Evidence Retriever
        email = pubmed_email or os.getenv("PUBMED_EMAIL")
        pubmed_api_key = pubmed_api_key or os.getenv("PUBMED_API_KEY")

        if email and pubmed_api_key:
            pubmed_client = PubMedAPI(email=email, api_key=pubmed_api_key)
            self.evidence_retriever = EvidenceRetriever(
                pubmed_client=pubmed_client, max_results=5
            )
        else:
            print("  Warning: No PubMed email provided, evidence retrieval disabled")
            self.evidence_retriever = None

        # 4. Prompt Templates
        self.prompt_templates = PromptTemplates()

        # 5. Insight Generator
        self.insight_generator = InsightGenerator(
            llm_client=self.gen_llm,
            evidence_retriever=self.evidence_retriever,
            prompt_template=self.prompt_templates,
        )

        # 6. Validator
        self.validator = InsightValidator()

        # 7. Evaluator
        self.evaluator = InsightEvaluator(
            llm=self.eval_llm, prompt_templates=self.prompt_templates
        )

        # Pipeline statistics
        self.stats = {
            "total_cohorts": 0,
            "total_combinations": 0,
            "total_insights_generated": 0,
            "total_insights_validated": 0,
            "total_insights_evaluated": 0,
            "validation_pass_rate": 0.0,
            "average_evaluation_score": 0.0,
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0,
        }

        print("Pipeline initialized successfully!")

    def run(
        self,
        max_cohorts: Optional[int] = None,
        insights_per_call: int = 5,
        skip_validation: bool = False,
        skip_evaluation: bool = False,
        output_dir: str = "output",
        rate_limit_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline.

        Args:
            max_cohorts: Maximum number of cohorts to process (None = all)
            num_templates: Number of insight templates to sample
            num_domains: Number of health domains to sample
            insights_per_call: Number of insights per call
            skip_validation: Skip validation step
            skip_evaluation: Skip evaluation step
            output_dir: Output directory for results
            rate_limit_delay: Delay between API calls (seconds)

        Returns:
            Pipeline summary with statistics
        """
        self.stats["start_time"] = datetime.now().isoformat()
        start_time = time.time()

        print("\n" + "=" * 80)
        print("DYK INSIGHT GENERATION PIPELINE")
        print("=" * 80)
        print(f"Market: {self.market}")
        print(f"Generation Model: {self.generation_model}")
        print(f"Evaluation Model: {self.evaluation_model}")
        print(f"Max cohorts: {max_cohorts or 'All'}")
        print(f"Insights per call: {insights_per_call}")
        print("=" * 80 + "\n")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Generate cohorts
        print("[STEP 1] Generating cohorts...")
        cohorts = self.cohort_generator.generate_priority_cohorts()
        if max_cohorts:
            cohorts = cohorts[:max_cohorts]

        self.stats["total_cohorts"] = len(cohorts)
        print(f"  Generated {len(cohorts)} cohorts")

        # Save cohorts
        cohorts_file = os.path.join(output_dir, "cohorts.json")
        with open(cohorts_file, "w") as f:
            json.dump(cohorts, f, indent=2)
        print(f"  Saved to {cohorts_file}\n")

        insight_templates = self.config_loader.insight_templates
        health_domains = self.config_loader.health_domains

        # Calculate total combinations
        total_combinations = len(cohorts) * len(insight_templates)
        self.stats["total_combinations"] = total_combinations
        expected_insights = total_combinations * insights_per_call

        print(f"  Total combinations: {total_combinations}")
        print(f"  Expected insights: {expected_insights}\n")

        # Step 2: Generate insights for all combinations
        print("[STEP 2] Generating insights...")
        all_insights = []
        sources = self.config_loader.sources

        combination_idx = 0
        for cohort in cohorts:
            for insight_template in insight_templates.values():
                combination_idx += 1
                print(
                    f"  [{combination_idx}/{total_combinations}] "
                    f"Cohort: {cohort['cohort_id']} | "
                    f"Template: {insight_template['type']} | "
                )

                try:
                    # Generate insights
                    insights_data = self.insight_generator.generate(
                        cohort=cohort,
                        insight_template=insight_template,
                        health_domains=health_domains,
                        sources=sources,
                        region=self.market,
                        num_insights=insights_per_call,
                        model=self.generation_model,
                        temperature=self.generation_temperature,
                        max_tokens=self.generation_max_tokens,
                    )

                    # Parse insights (handle both list and dict responses)
                    if isinstance(insights_data, dict) and "insights" in insights_data:
                        insights_list = insights_data["insights"]
                    elif isinstance(insights_data, list):
                        insights_list = insights_data
                    else:
                        insights_list = [insights_data]

                    # Add metadata to each insight
                    for insight in insights_list:
                        insight["metadata"] = {
                            "cohort": cohort,
                            "insight_template": insight_template,
                            "region": self.market,
                            "generation_model": self.generation_model,
                            "generation_temperature": self.generation_temperature,
                            "generation_max_tokens": self.generation_max_tokens,
                            "generation_timestamp": datetime.now().isoformat(),
                        }
                        all_insights.append(insight)

                    print(f"Generated {len(insights_list)} insights")
                    self.stats["total_insights_generated"] += len(insights_list)

                except Exception as e:
                    print(f"ERROR: {str(e)}")

                # Rate limiting
                time.sleep(rate_limit_delay)

        print(f"\n  Total insights generated: {len(all_insights)}\n")

        # Save raw insights
        raw_insights_file = os.path.join(output_dir, "insights_raw.json")
        with open(raw_insights_file, "w") as f:
            json.dump(
                {
                    "generated_at": datetime.now().isoformat(),
                    "total_insights": len(all_insights),
                    "insights": all_insights,
                },
                f,
                indent=2,
            )
        print(f"  Saved raw insights to {raw_insights_file}\n")

        # Step 3: Validate insights
        validated_insights = []
        if not skip_validation:
            print("[STEP 3] Validating insights...")
            for idx, insight in enumerate(all_insights, 1):
                print(f"[{idx}/{len(all_insights)}] Validating insight...")

                try:
                    validation_result = self.validator.validate(insight)
                    insight["validation"] = {
                        "validated": validation_result["validated"],
                        "number_failed": validation_result["number_failed"],
                        "checks": validation_result["checks"],
                        "validation_timestamp": datetime.now().isoformat(),
                    }

                    if validation_result["validated"]:
                        validated_insights.append(insight)
                        print("PASS")
                    else:
                        print(
                            f"FAIL - {validation_result['number_failed']} checks failed"
                        )

                    self.stats["total_insights_validated"] += 1

                except Exception as e:
                    print(f"ERROR during validation: {str(e)}")
                    insight["validation"] = {
                        "validated": False,
                        "error": str(e),
                        "validation_timestamp": datetime.now().isoformat(),
                    }

            self.stats["validation_pass_rate"] = (
                len(validated_insights) / len(all_insights) * 100
                if all_insights
                else 0.0
            )

            print(
                f"\nValidation complete: {len(validated_insights)}/{len(all_insights)} passed "
                f"({self.stats['validation_pass_rate']:.1f}%)\n"
            )

            # Save all insights with validation results (including failures)
            all_validated_file = os.path.join(
                output_dir, "insights_post_validation.json"
            )
            with open(all_validated_file, "w") as f:
                json.dump(
                    {
                        "generated_at": datetime.now().isoformat(),
                        "total_insights": len(all_insights),
                        "passed": len(validated_insights),
                        "failed": len(all_insights) - len(validated_insights),
                        "insights": all_insights,
                    },
                    f,
                    indent=2,
                )
            print(f"Saved all insights after validation to {all_validated_file}")

            # Save only validated insights (passed)
            validated_insights_file = os.path.join(
                output_dir, "insights_validated.json"
            )
            with open(validated_insights_file, "w") as f:
                json.dump(
                    {
                        "generated_at": datetime.now().isoformat(),
                        "total_insights": len(validated_insights),
                        "insights": validated_insights,
                    },
                    f,
                    indent=2,
                )
            print(
                f"Saved validated insights (passed only) to {validated_insights_file}\n"
            )
        else:
            validated_insights = all_insights
            print("[STEP 4] Skipped validation\n")

        # Step 4: Evaluate insights (only those that passed validation)
        evaluated_insights = []
        if not skip_evaluation and validated_insights:
            print("[STEP 4] Evaluating insights...")
            evaluation_scores = []

            for idx, insight in enumerate(validated_insights, 1):
                print(f"[{idx}/{len(validated_insights)}] Evaluating insight...")

                try:
                    # Get cohort and template info from metadata
                    cohort = insight["metadata"].get("cohort")
                    insight_template = insight["metadata"].get("insight_template")

                    if cohort and insight_template:
                        evaluation_result = self.evaluator.evaluate(
                            insight=insight,
                            cohort=cohort,
                            insight_template=insight_template,
                            region=self.market,
                            model=self.evaluation_model,
                            temperature=0.3,  # Lower temperature for evaluation
                            max_tokens=3000,  # Sufficient tokens for evaluation
                        )

                        # Parse evaluation result
                        if isinstance(evaluation_result, str):
                            try:
                                evaluation_result = json.loads(evaluation_result)
                            except json.JSONDecodeError:
                                evaluation_result = {"raw_response": evaluation_result}

                        insight["evaluation"] = {
                            "result": evaluation_result,
                            "evaluation_model": self.evaluation_model,
                            "evaluation_timestamp": datetime.now().isoformat(),
                        }

                        # Try to extract score
                        if isinstance(evaluation_result, dict):
                            score = evaluation_result.get(
                                "overall_score", evaluation_result.get("score")
                            )
                            if score is not None:
                                evaluation_scores.append(float(score))
                                print(f"Evaluation Score: {score}")
                            else:
                                print("Evaluated (no numeric score)")
                        else:
                            print("Evaluated (not a dictionary result)")

                        evaluated_insights.append(insight)
                        self.stats["total_insights_evaluated"] += 1

                    else:
                        print("SKIP - Missing metadata")

                    # Rate limiting
                    time.sleep(rate_limit_delay)

                except Exception as e:
                    print(f"ERROR during evaluation: {str(e)}")
                    insight["evaluation"] = {
                        "error": str(e),
                        "evaluation_timestamp": datetime.now().isoformat(),
                    }
                    evaluated_insights.append(insight)

            if evaluation_scores:
                self.stats["average_evaluation_score"] = sum(evaluation_scores) / len(
                    evaluation_scores
                )
                print(
                    f"\nEvaluation complete: {len(evaluated_insights)} insights evaluated"
                )
                print(f"Average score: {self.stats['average_evaluation_score']:.2f}\n")
            else:
                print(
                    f"\nEvaluation complete: {len(evaluated_insights)} insights evaluated\n"
                )

            # Save evaluated insights
            evaluated_insights_file = os.path.join(output_dir, "insights_final.json")
            with open(evaluated_insights_file, "w") as f:
                json.dump(
                    {
                        "generated_at": datetime.now().isoformat(),
                        "total_insights": len(evaluated_insights),
                        "insights": evaluated_insights,
                    },
                    f,
                    indent=2,
                )
            print(f"Saved final insights to {evaluated_insights_file}\n")
        else:
            evaluated_insights = validated_insights
            if skip_evaluation:
                print("[STEP 4] Skipped evaluation\n")
            else:
                print("[STEP 4] No validated insights to evaluate\n")

        # Calculate final statistics
        end_time = time.time()
        self.stats["end_time"] = datetime.now().isoformat()
        self.stats["duration_seconds"] = end_time - start_time

        # Save pipeline summary
        summary = {
            "pipeline_config": {
                "market": self.market,
                "generation_model": self.generation_model,
                "evaluation_model": self.evaluation_model,
                "generation_temperature": self.generation_temperature,
                "generation_max_tokens": self.generation_max_tokens,
                "max_cohorts": max_cohorts,
                "insights_per_call": insights_per_call,
                "region": self.market,
                "skip_validation": skip_validation,
                "skip_evaluation": skip_evaluation,
            },
            "statistics": self.stats,
            "output_files": {
                "cohorts": cohorts_file,
                "raw_insights": raw_insights_file,
                "insights_post_validation": all_validated_file
                if not skip_validation
                else None,
                "validated_insights": validated_insights_file
                if not skip_validation
                else None,
                "final_insights": evaluated_insights_file
                if not skip_evaluation
                else None,
            },
        }

        summary_file = os.path.join(output_dir, "pipeline_summary.json")
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        # Print final summary
        print("=" * 80)
        print("PIPELINE COMPLETE")
        print("=" * 80)
        print(f"Duration: {self.stats['duration_seconds'] / 60:.2f} minutes")
        print(f"Cohorts processed: {self.stats['total_cohorts']}")
        print(f"Total combinations: {self.stats['total_combinations']}")
        print(f"Insights generated: {self.stats['total_insights_generated']}")
        if not skip_validation:
            print(
                f"Insights validated: {self.stats['total_insights_validated']} "
                f"({self.stats['validation_pass_rate']:.1f}% pass rate)"
            )
        if not skip_evaluation:
            print(f"Insights evaluated: {self.stats['total_insights_evaluated']}")
            if self.stats["average_evaluation_score"] > 0:
                print(
                    f"Average evaluation score: {self.stats['average_evaluation_score']:.2f}"
                )
        # Export insights to CSV for easy viewing
        csv_file = self._export_to_csv(evaluated_insights, output_dir)
        if csv_file:
            print(f"CSV export saved to: {csv_file}")

        print(f"\nAll outputs saved to: {output_dir}/")
        print(f"Summary saved to: {summary_file}")
        print("=" * 80 + "\n")

        return summary

    def _export_to_csv(
        self, insights: List[Dict[str, Any]], output_dir: str
    ) -> Optional[str]:
        """
        Export insights to CSV format for easy viewing and analysis.

        Args:
            insights: List of insight dictionaries
            output_dir: Output directory

        Returns:
            Path to CSV file or None if export failed
        """
        if not insights:
            print("No insights to export to CSV")

        csv_file = os.path.join(output_dir, "insights_final.csv")

        try:
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # header row
                writer.writerow(
                    [
                        "full_insight",
                        "hook",
                        "explanation",
                        "action",
                        "source_name",
                        "source_url",
                        "cohort_params",
                        "cohort_desc",
                        "insight_template",
                        "gen_model",
                        "gen_temperature",
                        "gen_max_tokens",
                        "generated_at",
                        "eval_score",
                        "factual_accuracy",
                        "safety",
                        "faithfulness",
                        "relevance",
                        "actionability",
                        "cultural_appropriateness",
                        "recommendation",
                        "revision_suggestions",
                        "eval_model",
                        "evaluated_at",
                    ]
                )

                for idx, insight in enumerate(insights, 1):
                    # Extract metadata
                    metadata = insight.get("metadata", {})
                    cohort = metadata.get("cohort", {})
                    template = metadata.get("insight_template", {})
                    eval = insight.get("evaluation", {})
                    eval_result = eval.get("result", {})

                    writer.writerow(
                        [
                            " ".join(
                                [
                                    insight.get("hook", ""),
                                    insight.get("explanation", ""),
                                    insight.get("action", ""),
                                ]
                            ),  # full insight
                            insight.get("hook", ""),  # hook
                            insight.get("explanation", ""),  # explanation
                            insight.get("action", ""),  # action
                            insight.get("source_name", ""),  # source name
                            insight.get("source_url", ""),  # source url
                            cohort.get("cohort_params", ""),  # cohort params
                            cohort.get("description", ""),  # cohort desc
                            template.get("type", ""),  # insight_template
                            metadata.get("generation_model", ""),  # generation model
                            metadata.get(
                                "generation_temperature", ""
                            ),  # generation temperature
                            metadata.get(
                                "generation_max_tokens", ""
                            ),  # generation max tokens
                            metadata.get(
                                "generation_timestamp", ""
                            ),  # generation timestamp
                            eval_result.get("overall_score", ""),  # eval overall score
                            eval_result.get("factual_accuracy", {}).get(
                                "score", ""
                            ),  # factual accuracy score
                            eval_result.get("safety", {}).get(
                                "score", ""
                            ),  # safety score
                            eval_result.get("source_faithfulness", {}).get(
                                "score", ""
                            ),  # faithfulness score
                            eval_result.get("relevance", {}).get(
                                "score", ""
                            ),  # relevance score
                            eval_result.get("actionability", {}).get(
                                "score", ""
                            ),  # actionability score
                            eval_result.get("cultural_appropriateness", {}).get(
                                "score", ""
                            ),  # culture appropriateness score
                            eval_result.get("recommendation", ""),  # recommendation
                            eval_result.get(
                                "revision_suggestions", ""
                            ),  # revision suggestions
                            eval.get("evaluation_model", ""),  # eval model
                            eval.get("evaluation_timestamp", ""),  # eval timestamp
                        ]
                    )

            print(f"\n✓ Exported {len(insights)} insights to CSV")
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return None

    # def run(
    #     self,
    #     max_cohorts: Optional[int] = None,
    #     num_templates: int = 3,
    #     num_domains: int = 3,
    #     insights_per_call: int = 2,
    #     skip_validation: bool = False,
    #     skip_evaluation: bool = False,
    #     output_dir: str = "output",
    #     rate_limit_delay: float = 1.0,
    # ) -> Dict[str, Any]:
    #     """
    #     Run the complete pipeline.

    #     Args:
    #         max_cohorts: Maximum number of cohorts to process (None = all)
    #         num_templates: Number of insight templates to sample
    #         num_domains: Number of health domains to sample
    #         insights_per_call: Number of insights per call
    #         skip_validation: Skip validation step
    #         skip_evaluation: Skip evaluation step
    #         output_dir: Output directory for results
    #         rate_limit_delay: Delay between API calls (seconds)

    #     Returns:
    #         Pipeline summary with statistics
    #     """
    #     self.stats["start_time"] = datetime.now().isoformat()
    #     start_time = time.time()

    #     print("\n" + "=" * 80)
    #     print("DYK INSIGHT GENERATION PIPELINE")
    #     print("=" * 80)
    #     print(f"Market: {self.market}")
    #     print(f"Model: {self.model}")
    #     print(f"Max cohorts: {max_cohorts or 'All'}")
    #     print(f"Templates: {num_templates}")
    #     print(f"Domains: {num_domains}")
    #     print(f"Insights per call: {insights_per_call}")
    #     print("=" * 80 + "\n")

    #     # Create output directory
    #     os.makedirs(output_dir, exist_ok=True)

    #     # Step 1: Generate cohorts
    #     print("[STEP 1] Generating cohorts...")
    #     cohorts = self.cohort_generator.generate_priority_cohorts()
    #     if max_cohorts:
    #         cohorts = cohorts[:max_cohorts]

    #     self.stats["total_cohorts"] = len(cohorts)
    #     print(f"  Generated {len(cohorts)} cohorts")

    #     # Save cohorts
    #     cohorts_file = os.path.join(output_dir, "cohorts.json")
    #     with open(cohorts_file, "w") as f:
    #         json.dump(cohorts, f, indent=2)
    #     print(f"  Saved to {cohorts_file}\n")

    #     # Calculate total combinations
    #     total_combinations = len(cohorts) * num_templates * num_domains
    #     self.stats["total_combinations"] = total_combinations
    #     expected_insights = total_combinations * insights_per_call

    #     print(f"  Total combinations: {total_combinations}")
    #     print(f"  Expected insights: {expected_insights}\n")

    #     # Step 2: Generate insights for all combinations
    #     print("[STEP 2] Generating insights...")
    #     all_insights = []
    #     sources = self.config_loader.sources

    #     combination_idx = 0
    #     for cohort in cohorts:
    #         sampled_templates = self.config_loader.sample_insight_templates(
    #             n=num_templates
    #         )
    #         for insight_template in sampled_templates:
    #             sampled_domains = self.config_loader.sample_health_domains(
    #                 n=num_domains
    #             )
    #             for health_domain in sampled_domains:
    #                 combination_idx += 1
    #                 print(
    #                     f"  [{combination_idx}/{total_combinations}] "
    #                     f"Cohort: {cohort['cohort_id']} | "
    #                     f"Template: {insight_template['type']} | "
    #                     f"Domain: {health_domain['name']}"
    #                 )

    #                 try:
    #                     # Generate insights
    #                     insights_data = self.insight_generator.generate(
    #                         cohort=cohort,
    #                         insight_template=insight_template,
    #                         health_domain=health_domain,
    #                         sources=sources,
    #                         region=self.market,
    #                         num_insights=insights_per_call,
    #                         model=self.generation_model,
    #                         temperature=self.generation_temperature,
    #                         max_tokens=self.generation_max_tokens,
    #                     )

    #                     # Parse insights (handle both list and dict responses)
    #                     if (
    #                         isinstance(insights_data, dict)
    #                         and "insights" in insights_data
    #                     ):
    #                         insights_list = insights_data["insights"]
    #                     elif isinstance(insights_data, list):
    #                         insights_list = insights_data
    #                     else:
    #                         insights_list = [insights_data]

    #                     # Add metadata to each insight
    #                     for insight in insights_list:
    #                         insight["metadata"] = {
    #                             "cohort": cohort,
    #                             "insight_template": insight_template,
    #                             "health_domain": health_domain,
    #                             "region": self.market,
    #                             "generation_model": self.generation_model,
    #                             "generation_temperature": self.generation_temperature,
    #                             "generation_max_tokens": self.generation_max_tokens,
    #                             "generation_timestamp": datetime.now().isoformat(),
    #                         }
    #                         all_insights.append(insight)

    #                     print(f"Generated {len(insights_list)} insights")
    #                     self.stats["total_insights_generated"] += len(insights_list)

    #                 except Exception as e:
    #                     print(f"ERROR: {str(e)}")

    #                 # Rate limiting
    #                 time.sleep(rate_limit_delay)

    #     print(f"\n  Total insights generated: {len(all_insights)}\n")

    #     # Save raw insights
    #     raw_insights_file = os.path.join(output_dir, "insights_raw.json")
    #     with open(raw_insights_file, "w") as f:
    #         json.dump(
    #             {
    #                 "generated_at": datetime.now().isoformat(),
    #                 "total_insights": len(all_insights),
    #                 "insights": all_insights,
    #             },
    #             f,
    #             indent=2,
    #         )
    #     print(f"  Saved raw insights to {raw_insights_file}\n")

    #     # Step 3: Validate insights
    #     validated_insights = []
    #     if not skip_validation:
    #         print("[STEP 3] Validating insights...")
    #         for idx, insight in enumerate(all_insights, 1):
    #             print(f"[{idx}/{len(all_insights)}] Validating insight...")

    #             try:
    #                 validation_result = self.validator.validate(insight)
    #                 insight["validation"] = {
    #                     "validated": validation_result["validated"],
    #                     "number_failed": validation_result["number_failed"],
    #                     "checks": validation_result["checks"],
    #                     "validation_timestamp": datetime.now().isoformat(),
    #                 }

    #                 if validation_result["validated"]:
    #                     validated_insights.append(insight)
    #                     print("PASS")
    #                 else:
    #                     print(
    #                         f"FAIL - {validation_result['number_failed']} checks failed"
    #                     )

    #                 self.stats["total_insights_validated"] += 1

    #             except Exception as e:
    #                 print(f"ERROR during validation: {str(e)}")
    #                 insight["validation"] = {
    #                     "validated": False,
    #                     "error": str(e),
    #                     "validation_timestamp": datetime.now().isoformat(),
    #                 }

    #         self.stats["validation_pass_rate"] = (
    #             len(validated_insights) / len(all_insights) * 100
    #             if all_insights
    #             else 0.0
    #         )

    #         print(
    #             f"\nValidation complete: {len(validated_insights)}/{len(all_insights)} passed "
    #             f"({self.stats['validation_pass_rate']:.1f}%)\n"
    #         )

    #         # Save all insights with validation results (including failures)
    #         all_validated_file = os.path.join(
    #             output_dir, "insights_post_validation.json"
    #         )
    #         with open(all_validated_file, "w") as f:
    #             json.dump(
    #                 {
    #                     "generated_at": datetime.now().isoformat(),
    #                     "total_insights": len(all_insights),
    #                     "passed": len(validated_insights),
    #                     "failed": len(all_insights) - len(validated_insights),
    #                     "insights": all_insights,
    #                 },
    #                 f,
    #                 indent=2,
    #             )
    #         print(f"Saved all insights after validation to {all_validated_file}")

    #         # Save only validated insights (passed)
    #         validated_insights_file = os.path.join(
    #             output_dir, "insights_validated.json"
    #         )
    #         with open(validated_insights_file, "w") as f:
    #             json.dump(
    #                 {
    #                     "generated_at": datetime.now().isoformat(),
    #                     "total_insights": len(validated_insights),
    #                     "insights": validated_insights,
    #                 },
    #                 f,
    #                 indent=2,
    #             )
    #         print(
    #             f"Saved validated insights (passed only) to {validated_insights_file}\n"
    #         )
    #     else:
    #         validated_insights = all_insights
    #         print("[STEP 4] Skipped validation\n")

    #     # Step 4: Evaluate insights (only those that passed validation)
    #     evaluated_insights = []
    #     if not skip_evaluation and validated_insights:
    #         print("[STEP 4] Evaluating insights...")
    #         evaluation_scores = []

    #         for idx, insight in enumerate(validated_insights, 1):
    #             print(f"[{idx}/{len(validated_insights)}] Evaluating insight...")

    #             try:
    #                 # Get cohort and template info from metadata
    #                 cohort = insight["metadata"].get("cohort")
    #                 insight_template = insight["metadata"].get("insight_template")
    #                 health_domain = insight["metadata"].get("health_domain")

    #                 if cohort and insight_template and health_domain:
    #                     evaluation_result = self.evaluator.evaluate(
    #                         insight=insight,
    #                         cohort=cohort,
    #                         insight_template=insight_template,
    #                         health_domain=health_domain,
    #                         region=self.market,
    #                         model=self.evaluation_model,
    #                         temperature=0.3,  # Lower temperature for evaluation
    #                         max_tokens=2000,  # Sufficient tokens for evaluation
    #                     )

    #                     # Parse evaluation result
    #                     if isinstance(evaluation_result, str):
    #                         try:
    #                             evaluation_result = json.loads(evaluation_result)
    #                         except json.JSONDecodeError:
    #                             evaluation_result = {"raw_response": evaluation_result}

    #                     insight["evaluation"] = {
    #                         "result": evaluation_result,
    #                         "evaluation_model": self.evaluation_model,
    #                         "evaluation_timestamp": datetime.now().isoformat(),
    #                     }

    #                     # Try to extract score
    #                     if isinstance(evaluation_result, dict):
    #                         score = evaluation_result.get(
    #                             "overall_score", evaluation_result.get("score")
    #                         )
    #                         if score is not None:
    #                             evaluation_scores.append(float(score))
    #                             print(f"Evaluation Score: {score}")
    #                         else:
    #                             print("Evaluated (no numeric score)")
    #                     else:
    #                         print("Evaluated (not a dictionary result)")

    #                     evaluated_insights.append(insight)
    #                     self.stats["total_insights_evaluated"] += 1

    #                 else:
    #                     print("SKIP - Missing metadata")

    #                 # Rate limiting
    #                 time.sleep(rate_limit_delay)

    #             except Exception as e:
    #                 print(f"ERROR during evaluation: {str(e)}")
    #                 insight["evaluation"] = {
    #                     "error": str(e),
    #                     "evaluation_timestamp": datetime.now().isoformat(),
    #                 }
    #                 evaluated_insights.append(insight)

    #         if evaluation_scores:
    #             self.stats["average_evaluation_score"] = sum(evaluation_scores) / len(
    #                 evaluation_scores
    #             )
    #             print(
    #                 f"\nEvaluation complete: {len(evaluated_insights)} insights evaluated"
    #             )
    #             print(f"Average score: {self.stats['average_evaluation_score']:.2f}\n")
    #         else:
    #             print(
    #                 f"\nEvaluation complete: {len(evaluated_insights)} insights evaluated\n"
    #             )

    #         # Save evaluated insights
    #         evaluated_insights_file = os.path.join(output_dir, "insights_final.json")
    #         with open(evaluated_insights_file, "w") as f:
    #             json.dump(
    #                 {
    #                     "generated_at": datetime.now().isoformat(),
    #                     "total_insights": len(evaluated_insights),
    #                     "insights": evaluated_insights,
    #                 },
    #                 f,
    #                 indent=2,
    #             )
    #         print(f"Saved final insights to {evaluated_insights_file}\n")
    #     else:
    #         evaluated_insights = validated_insights
    #         if skip_evaluation:
    #             print("[STEP 4] Skipped evaluation\n")
    #         else:
    #             print("[STEP 4] No validated insights to evaluate\n")

    #     # Calculate final statistics
    #     end_time = time.time()
    #     self.stats["end_time"] = datetime.now().isoformat()
    #     self.stats["duration_seconds"] = end_time - start_time

    #     # Save pipeline summary
    #     summary = {
    #         "pipeline_config": {
    #             "market": self.market,
    #             "generation_model": self.generation_model,
    #             "evaluation_model": self.evaluation_model,
    #             "generation_temperature": self.generation_temperature,
    #             "generation_max_tokens": self.generation_max_tokens,
    #             "max_cohorts": max_cohorts,
    #             "num_templates": num_templates,
    #             "num_domains": num_domains,
    #             "insights_per_call": insights_per_call,
    #             "region": self.market,
    #             "skip_validation": skip_validation,
    #             "skip_evaluation": skip_evaluation,
    #         },
    #         "statistics": self.stats,
    #         "output_files": {
    #             "cohorts": cohorts_file,
    #             "raw_insights": raw_insights_file,
    #             "insights_post_validation": all_validated_file
    #             if not skip_validation
    #             else None,
    #             "validated_insights": validated_insights_file
    #             if not skip_validation
    #             else None,
    #             "final_insights": evaluated_insights_file
    #             if not skip_evaluation
    #             else None,
    #         },
    #     }

    #     summary_file = os.path.join(output_dir, "pipeline_summary.json")
    #     with open(summary_file, "w") as f:
    #         json.dump(summary, f, indent=2)

    #     # Print final summary
    #     print("=" * 80)
    #     print("PIPELINE COMPLETE")
    #     print("=" * 80)
    #     print(f"Duration: {self.stats['duration_seconds'] / 60:.2f} minutes")
    #     print(f"Cohorts processed: {self.stats['total_cohorts']}")
    #     print(f"Total combinations: {self.stats['total_combinations']}")
    #     print(f"Insights generated: {self.stats['total_insights_generated']}")
    #     if not skip_validation:
    #         print(
    #             f"Insights validated: {self.stats['total_insights_validated']} "
    #             f"({self.stats['validation_pass_rate']:.1f}% pass rate)"
    #         )
    #     if not skip_evaluation:
    #         print(f"Insights evaluated: {self.stats['total_insights_evaluated']}")
    #         if self.stats["average_evaluation_score"] > 0:
    #             print(
    #                 f"Average evaluation score: {self.stats['average_evaluation_score']:.2f}"
    #             )
    #     print(f"\nAll outputs saved to: {output_dir}/")
    #     print(f"Summary saved to: {summary_file}")
    #     print("=" * 80 + "\n")

    #     return summary


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DYK Insight Generation Pipeline - End-to-end workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Configuration
    parser.add_argument(
        "--market",
        default="singapore",
        help="Target market/region (default: singapore)",
    )
    parser.add_argument(
        "--gen_model", default="x-ai/grok-4.1-fast", help="LLM model for generation"
    )

    parser.add_argument(
        "--eval_model", default="x-ai/grok-4.1-fast", help="LLM model for evaluation"
    )
    parser.add_argument(
        "--gen_temperature",
        type=float,
        default=0.7,
        help="LLM temperature for generation",
    )
    parser.add_argument(
        "--gen_max_tokens",
        type=int,
        default=2000,
        help="Max tokens for LLM generation",
    )

    # Generation parameters
    parser.add_argument(
        "--max_cohorts",
        type=int,
        help="Maximum number of cohorts to process (default: all)",
    )
    # parser.add_argument(
    #     "--num_templates",
    #     type=int,
    #     default=3,
    #     help="Number of insight templates to sample (default: 3)",
    # )
    # parser.add_argument(
    #     "--num_domains",
    #     type=int,
    #     default=3,
    #     help="Number of health domains to sample (default: 3)",
    # )
    parser.add_argument(
        "--insights_per_call",
        type=int,
        default=2,
        help="Number of insights per combination (default: 2)",
    )

    # Pipeline options
    parser.add_argument(
        "--skip_validation", action="store_true", help="Skip validation step"
    )
    parser.add_argument(
        "--skip_evaluation", action="store_true", help="Skip evaluation step"
    )
    parser.add_argument(
        "--output_dir", default="output", help="Output directory (default: output/)"
    )
    parser.add_argument(
        "--rate_limit_delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Initialize and run pipeline
    try:
        pipeline = DYKPipeline(
            market=args.market,
            generation_model=args.gen_model,
            evaluation_model=args.eval_model,
            generation_temperature=args.gen_temperature,
            generation_max_tokens=args.gen_max_tokens,
        )

        summary = pipeline.run(
            max_cohorts=args.max_cohorts,
            # num_templates=args.num_templates,
            # num_domains=args.num_domains,
            insights_per_call=args.insights_per_call,
            skip_validation=args.skip_validation,
            skip_evaluation=args.skip_evaluation,
            output_dir=args.output_dir,
            rate_limit_delay=args.rate_limit_delay,
        )

        print("\nPipeline completed successfully!")
        return summary

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nPipeline failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
