import os

# Definizione della struttura completa come da specifica
HUB_STRUCTURE = {
    "00_IDEA_VALIDATION": [
        "problem_definition.md", "solution_hypothesis.md", "target_audience_personas.md",
        "customer_interviews_template.md", "survey_questions.md", "validation_metrics.md",
        "pivot_decision_framework.md"
    ],
    "01_MARKET_RESEARCH": [
        "market_size_analysis.md", "industry_trends_report.md", "competitor_matrix.md",
        "competitive_advantage_analysis.md", "pricing_research.md", "regulatory_landscape.md",
        "market_entry_barriers.md"
    ],
    "02_BUSINESS_MODEL": [
        "lean_canvas.md", "business_model_canvas.md", "value_proposition_canvas.md",
        "revenue_streams.md", "cost_structure.md", "key_metrics_kpis.md",
        "unit_economics.md", "financial_projections.md"
    ],
    "03_PRODUCT_STRATEGY": [
        "mvp_definition.md", "feature_prioritization_matrix.md", "user_stories.md",
        "product_roadmap.md", "tech_stack_recommendations.md", "architecture_overview.md",
        "mvp_budget_low_cost.md", "build_vs_buy_analysis.md", "development_timeline.md"
    ],
    "04_GO_TO_MARKET": [
        "gtm_strategy.md", "customer_acquisition_plan.md", "marketing_channels.md",
        "content_marketing_strategy.md", "sales_funnel.md", "pricing_strategy.md",
        "launch_checklist.md", "growth_hacking_tactics.md", "metrics_dashboard.md"
    ],
    "05_LEGAL_COMPLIANCE": [
        "incorporation_checklist.md", "shareholder_agreement_template.md", "equity_distribution_plan.md",
        "cap_table.md", "ip_protection_strategy.md", "nda_templates.md",
        "employee_contracts_template.md", "regulatory_compliance_checklist.md", "privacy_policy_gdpr.md"
    ],
    "06_FUNDRAISING": [
        "fundraising_strategy.md", "investor_targeting.md", "pitch_deck.md",
        "executive_summary.md", "elevator_pitch.md", "financial_model_investors.md",
        "term_sheet_template.md", "safe_agreement_template.md", "convertible_note_template.md",
        "due_diligence_checklist.md", "investor_faq.md", "investor_updates_template.md"
    ],
    "07_TEAM_OPERATIONS": [
        "organizational_structure.md", "hiring_plan.md", "job_descriptions.md",
        "onboarding_process.md", "company_culture_values.md", "okr_framework.md",
        "meeting_cadence.md", "remote_work_policy.md"
    ],
    "08_RISK_MANAGEMENT": [
        "risk_assessment_matrix.md", "mitigation_strategies.md", "contingency_plans.md",
        "insurance_requirements.md", "crisis_communication_plan.md"
    ],
    "09_TRACTION_METRICS": [
        "key_metrics_tracking.md", "experiment_log.md", "customer_feedback_repository.md",
        "pivot_history.md", "milestone_tracker.md"
    ],
    "10_SCALING_STRATEGY": [
        "expansion_plan.md", "internationalization_strategy.md", "partnership_opportunities.md",
        "exit_strategy.md", "succession_planning.md"
    ]
}

def generate_hub_structure(base_path, project_name):
    """
    Genera fisicamente le cartelle e i file template per un progetto.
    """
    root_dir = os.path.join(base_path, "HUB_AGENTS")
    
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)
        
    created_files = []

    for folder, files in HUB_STRUCTURE.items():
        folder_path = os.path.join(root_dir, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        for filename in files:
            file_path = os.path.join(folder_path, filename)
            if not os.path.exists(file_path):
                # Qui in futuro inseriremo i template veri e propri
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {filename.replace('.md', '').replace('_', ' ').title()}\n\n")
                    f.write("<!-- AI_GENERATED_TEMPLATE -->\n")
                    f.write(f"Status: 🔴 Not Started\n\n")
                    f.write("## Overview\n(AI will suggest content here...)\n")
                created_files.append(file_path)
                
    return created_files
