"""Insights Agent for LLM-powered analytics features."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.models.workflow import AgentResult, AgentStatus, WorkflowState
from src.services.llm.service import LLMService
from src.services.llm.base import LLMConfig, LLMProvider
from src.services.llm import prompts
from src.services.state_manager import StateManager

logger = logging.getLogger(__name__)


class InsightsAgent(BaseAgent):
    """
    Agent for generating LLM-powered insights including:
    - Executive summaries
    - Natural language query responses
    - Predictive narratives
    """

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        llm_service: Optional[LLMService] = None,
        llm_provider: str = "claude",
        llm_model: Optional[str] = None,
    ):
        """
        Initialize the Insights Agent.

        Args:
            state_manager: State manager for workflow state
            llm_service: Pre-configured LLM service (optional)
            llm_provider: LLM provider name if llm_service not provided
            llm_model: Model name if llm_service not provided
        """
        super().__init__(name="InsightsAgent", state_manager=state_manager)

        if llm_service:
            self.llm = llm_service
        else:
            self.llm = LLMService.create(
                provider=llm_provider,
                model=llm_model,
                temperature=0.7,
            )

    async def execute(self, workflow_state: WorkflowState) -> AgentResult:
        """
        Execute insights generation for a completed workflow.

        Generates executive summary and predictive narrative.
        """
        started_at = datetime.now()

        try:
            insights = {}

            # Generate executive summary if we have metrics
            if workflow_state.financial_metrics and workflow_state.quality_metrics:
                await self._log(
                    workflow_state.workflow_id,
                    "info",
                    "Generating executive summary..."
                )
                insights["executive_summary"] = await self.generate_executive_summary(
                    workflow_state
                )

            # Generate predictive narrative if we have predictions
            if workflow_state.predictions:
                await self._log(
                    workflow_state.workflow_id,
                    "info",
                    "Generating predictive narrative..."
                )
                insights["predictive_narrative"] = await self.generate_predictive_narrative(
                    workflow_state
                )

            return self._create_success_result(
                started_at=started_at,
                result_data={
                    "insights": insights,
                    "llm_provider": self.llm.provider_name,
                    "llm_model": self.llm.model_name,
                }
            )

        except Exception as e:
            logger.exception(f"Insights generation failed: {e}")
            return self._create_failure_result(
                started_at=started_at,
                error_message=str(e)
            )

    async def generate_executive_summary(
        self,
        workflow_state: WorkflowState,
    ) -> str:
        """
        Generate an executive summary from workflow results.

        Args:
            workflow_state: Completed workflow state with metrics

        Returns:
            Executive summary text
        """
        fm = workflow_state.financial_metrics
        qm = workflow_state.quality_metrics
        rm = workflow_state.risk_metrics

        # Format the prompt with workflow data
        prompt = prompts.EXECUTIVE_SUMMARY_PROMPT.format(
            contract_id=workflow_state.contract_id,
            performance_period=f"{self._month_name(workflow_state.performance_month)} {workflow_state.performance_year}",
            baseline_spending=fm.get("baseline_spending", 0),
            actual_spending=fm.get("actual_spending", 0),
            total_savings=fm.get("total_savings", 0),
            savings_pct=fm.get("savings_percentage", 0),
            shared_savings=fm.get("shared_savings_amount", 0),
            actual_pmpm=fm.get("actual_pmpm", 0),
            target_pmpm=fm.get("target_pmpm", 0),
            quality_score=qm.get("composite_score", 0),
            quality_threshold=qm.get("quality_threshold", 80),
            quality_gate_status=qm.get("quality_gate_status", "unknown"),
            preventive_score=qm.get("preventive_care_score", 0),
            chronic_score=qm.get("chronic_disease_score", 0),
            coordination_score=qm.get("care_coordination_score", 0),
            experience_score=qm.get("patient_experience_score", 0),
            total_members=rm.get("total_members", 0) if rm else 0,
            high_risk_pct=rm.get("high_risk_pct", 0) if rm else 0,
            avg_risk_score=rm.get("average_risk_score", 0) if rm else 0,
            er_per_1000=fm.get("er_visits_per_1000", 0),
            admits_per_1000=fm.get("admits_per_1000", 0),
            critical_errors=len(workflow_state.critical_errors),
            warnings=len(workflow_state.warnings),
            auto_fixes=workflow_state.auto_fixes_applied,
        )

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=prompts.EXECUTIVE_SUMMARY_SYSTEM,
            temperature=0.7,
        )

        return response.content

    async def generate_predictive_narrative(
        self,
        workflow_state: WorkflowState,
    ) -> str:
        """
        Generate a predictive narrative from workflow predictions.

        Args:
            workflow_state: Completed workflow state with predictions

        Returns:
            Predictive narrative text
        """
        pred = workflow_state.predictions
        fm = workflow_state.financial_metrics
        qm = workflow_state.quality_metrics

        # Format risk factors and opportunities
        risk_factors = "\n".join([
            f"- {r['title']}: {r['description']}"
            for r in pred.get("risks", [])
        ]) or "- No significant risks identified"

        opportunities = "\n".join([
            f"- {o['title']}: {o['description']}"
            for o in pred.get("opportunities", [])
        ]) or "- No specific opportunities identified"

        prompt = prompts.PREDICTIVE_NARRATIVE_PROMPT.format(
            current_month=pred.get("current_month", 1),
            ytd_savings=fm.get("total_savings", 0),
            ytd_savings_pct=fm.get("savings_percentage", 0),
            current_quality=qm.get("composite_score", 0),
            projected_savings=pred.get("projected_year_end_savings", 0),
            projected_shared_savings=pred.get("projected_shared_savings", 0),
            savings_probability=pred.get("probability_meeting_target", 0),
            quality_probability=pred.get("probability_quality_gate", 0),
            savings_lower=pred.get("savings_lower_bound", 0),
            savings_upper=pred.get("savings_upper_bound", 0),
            risk_factors=risk_factors,
            opportunities=opportunities,
        )

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=prompts.PREDICTIVE_NARRATIVE_SYSTEM,
            temperature=0.7,
        )

        return response.content

    async def answer_query(
        self,
        question: str,
        workflow_state: Optional[WorkflowState] = None,
        metrics_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Answer a natural language query about the data.

        Args:
            question: User's natural language question
            workflow_state: Optional workflow state for context
            metrics_context: Optional pre-formatted metrics context

        Returns:
            Dictionary with answer and metadata
        """
        # Build context from workflow state if provided
        if metrics_context is None and workflow_state:
            metrics_context = self._build_metrics_context(workflow_state)
        elif metrics_context is None:
            metrics_context = {"note": "No workflow data available"}

        context_str = json.dumps(metrics_context, indent=2, default=str)

        system_prompt = prompts.NATURAL_LANGUAGE_QUERY_SYSTEM.format(
            metrics_context=context_str
        )

        prompt = prompts.NATURAL_LANGUAGE_QUERY_PROMPT.format(
            question=question
        )

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,  # Lower temperature for factual queries
            use_cache=False,  # Don't cache queries
        )

        return {
            "question": question,
            "answer": response.content,
            "model": response.model,
            "provider": response.provider.value,
            "tokens_used": response.input_tokens + response.output_tokens,
        }

    async def explain_validation_error(
        self,
        error_type: str,
        dataset: str,
        affected_count: int,
        affected_pct: float,
        error_details: Dict[str, Any],
    ) -> str:
        """
        Generate a plain-language explanation of a validation error.

        Args:
            error_type: Type of validation error
            dataset: Dataset where error occurred
            affected_count: Number of affected records
            affected_pct: Percentage of records affected
            error_details: Additional error details

        Returns:
            Plain-language explanation with remediation suggestions
        """
        prompt = prompts.ERROR_EXPLANATION_PROMPT.format(
            error_type=error_type,
            dataset=dataset,
            affected_count=affected_count,
            affected_pct=affected_pct,
            error_details=json.dumps(error_details, indent=2),
        )

        response = await self.llm.generate(
            prompt=prompt,
            temperature=0.5,
        )

        return response.content

    def _build_metrics_context(self, workflow_state: WorkflowState) -> Dict[str, Any]:
        """Build a metrics context dictionary from workflow state."""
        context = {
            "contract_id": workflow_state.contract_id,
            "performance_period": f"{workflow_state.performance_year}-{workflow_state.performance_month:02d}",
            "status": workflow_state.status.value,
        }

        if workflow_state.financial_metrics:
            context["financial"] = {
                "total_savings": workflow_state.financial_metrics.get("total_savings"),
                "savings_percentage": workflow_state.financial_metrics.get("savings_percentage"),
                "actual_spending": workflow_state.financial_metrics.get("actual_spending"),
                "pmpm": workflow_state.financial_metrics.get("actual_pmpm"),
                "er_visits_per_1000": workflow_state.financial_metrics.get("er_visits_per_1000"),
                "admits_per_1000": workflow_state.financial_metrics.get("admits_per_1000"),
            }

        if workflow_state.quality_metrics:
            context["quality"] = {
                "composite_score": workflow_state.quality_metrics.get("composite_score"),
                "gate_status": workflow_state.quality_metrics.get("quality_gate_status"),
                "measures": [
                    {
                        "name": m["measure_name"],
                        "rate": m["performance_rate"],
                        "benchmark": m["national_benchmark"],
                    }
                    for m in workflow_state.quality_metrics.get("measures", [])[:10]
                ],
            }

        if workflow_state.risk_metrics:
            context["population"] = {
                "total_members": workflow_state.risk_metrics.get("total_members"),
                "high_risk_count": workflow_state.risk_metrics.get("high_risk_count"),
                "high_risk_pct": workflow_state.risk_metrics.get("high_risk_pct"),
                "avg_risk_score": workflow_state.risk_metrics.get("average_risk_score"),
            }

        if workflow_state.records_extracted:
            context["data_volumes"] = workflow_state.records_extracted

        return context

    @staticmethod
    def _month_name(month: int) -> str:
        """Convert month number to name."""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        return months[month - 1] if 1 <= month <= 12 else str(month)
