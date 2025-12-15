code-chef-uat/
├── .github/
│ └── workflows/
│ ├── uat-suite.yml
│ └── screenshot-capture.yml
├── tests/
│ ├── unit/
│ │ ├── test_agent_supervisor.py
│ │ ├── test_agent_feature_dev.py
│ │ ├── test_agent_code_review.py
│ │ ├── test_agent_infrastructure.py
│ │ ├── test_agent_cicd.py
│ │ └── test_agent_documentation.py
│ ├── integration/
│ │ ├── test_workflow_pr_deployment.py
│ │ ├── test_workflow_hotfix.py
│ │ ├── test_mcp_tool_loading.py
│ │ └── test_event_bus.py
│ ├── e2e/
│ │ ├── test_full_workflow_with_screenshots.py
│ │ ├── test_hitl_approval.py
│ │ └── test_checkpoint_resume.py
│ └── fixtures/
│ ├── mock_agents.py
│ ├── sample_workflows.py
│ └── test_data.json
├── screenshots/
│ ├── baseline/
│ ├── current/
│ └── diff/
├── reports/
│ ├── html/
│ └── json/
├── config/
│ ├── pytest.ini
│ ├── playwright.config.js
│ └── test-scenarios.yaml
├── scripts/
│ ├── capture-screenshots.py
│ ├── generate-report.py
│ └── update-linear.py
├── docker-compose.yml
├── requirements.txt
├── README.md
└── .env.example
