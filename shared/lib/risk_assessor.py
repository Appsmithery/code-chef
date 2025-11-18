"""
Risk assessment for autonomous operations.
Determines whether tasks require human approval based on operation type, environment, and impact.
"""
from typing import Dict, Literal, Optional, List
import yaml
import os
import logging

logger = logging.getLogger(__name__)

RiskLevel = Literal["low", "medium", "high", "critical"]

class RiskAssessor:
    """
    Assesses risk level of autonomous operations to determine approval requirements.
    
    Uses configuration from config/hitl/risk-assessment-rules.yaml to evaluate:
    - Operation type (delete, deploy, modify)
    - Target environment (production, staging, dev)
    - Resource type (database, infrastructure, code)
    - Security findings
    - Cost estimates
    - Data sensitivity
    """
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "config", "hitl", "risk-assessment-rules.yaml"
            )
        
        try:
            with open(config_path) as f:
                self.rules = yaml.safe_load(f)
            logger.info(f"[RiskAssessor] Loaded rules from {config_path}")
        except FileNotFoundError:
            logger.error(f"[RiskAssessor] Config file not found: {config_path}")
            # Default minimal rules
            self.rules = {
                "risk_levels": {
                    "low": {"auto_approve": True},
                    "medium": {"auto_approve": False},
                    "high": {"auto_approve": False},
                    "critical": {"auto_approve": False}
                },
                "triggers": {}
            }
    
    def assess_task(self, task: Dict) -> RiskLevel:
        """
        Assess risk level of a task based on multiple factors.
        
        Args:
            task: Task dictionary containing:
                - operation: Operation type (delete, deploy, modify, etc.)
                - environment: Target environment (production, staging, dev)
                - resource_type: Resource being operated on
                - security_findings: List of security issues
                - estimated_cost: Estimated cost in dollars
                - data_sensitive: Boolean indicating sensitive data
                - metadata: Additional context
        
        Returns:
            RiskLevel enum value (low, medium, high, critical)
        """
        operation = task.get("operation", "").lower()
        environment = task.get("environment", "").lower()
        resource_type = task.get("resource_type", "").lower()
        
        # Critical triggers - highest priority
        if self._is_critical_operation(operation, environment, task):
            return "critical"
        
        # High-risk triggers
        if self._is_high_risk_operation(operation, environment, task):
            return "high"
        
        # Medium-risk triggers
        if self._is_medium_risk_operation(operation, environment, task):
            return "medium"
        
        # Default to low risk
        return "low"
    
    def _is_critical_operation(self, operation: str, environment: str, task: Dict) -> bool:
        """Check if operation is critical risk"""
        # Production deletions
        if operation == "delete" and environment == "production":
            return True
        
        # Database modifications in production
        if operation in ["modify", "delete"] and "database" in task.get("resource_type", "").lower() and environment == "production":
            return True
        
        # Critical security findings
        security_findings = task.get("security_findings", [])
        if any(f.get("severity") == "critical" for f in security_findings):
            return True
        
        # Data operations with sensitive data
        if task.get("data_sensitive") and operation in ["export", "delete", "modify"]:
            return True
        
        # Secret/permission modifications
        if operation in ["modify", "create", "delete"] and task.get("resource_type") in ["secret", "permission", "access_key"]:
            return True
        
        # Check configured triggers
        trigger_key = f"{operation}_{environment}"
        if self.rules.get("triggers", {}).get(trigger_key) == "critical":
            return True
        
        return False
    
    def _is_high_risk_operation(self, operation: str, environment: str, task: Dict) -> bool:
        """Check if operation is high risk"""
        # Production deployments
        if operation == "deploy" and environment == "production":
            return True
        
        # Infrastructure changes
        if operation in ["modify", "create", "delete"] and "infrastructure" in task.get("resource_type", "").lower():
            return True
        
        # High severity security findings
        security_findings = task.get("security_findings", [])
        if any(f.get("severity") == "high" for f in security_findings):
            return True
        
        # High cost operations
        estimated_cost = task.get("estimated_cost", 0)
        if estimated_cost > 1000:
            return True
        
        # Network/firewall changes
        if task.get("resource_type") in ["network", "firewall", "security_group"]:
            return True
        
        # Check configured triggers
        trigger_key = f"{operation}_{environment}"
        if self.rules.get("triggers", {}).get(trigger_key) == "high":
            return True
        
        return False
    
    def _is_medium_risk_operation(self, operation: str, environment: str, task: Dict) -> bool:
        """Check if operation is medium risk"""
        # Staging deployments
        if operation == "deploy" and environment == "staging":
            return True
        
        # Medium security findings
        security_findings = task.get("security_findings", [])
        if any(f.get("severity") == "medium" for f in security_findings):
            return True
        
        # Medium cost operations
        estimated_cost = task.get("estimated_cost", 0)
        if estimated_cost > 100:
            return True
        
        # Data imports
        if operation == "import" and task.get("resource_type") == "data":
            return True
        
        # Merging to main branch
        if operation == "merge" and task.get("target_branch") == "main":
            return True
        
        # Check configured triggers
        trigger_key = f"{operation}_{environment}"
        if self.rules.get("triggers", {}).get(trigger_key) == "medium":
            return True
        
        return False
    
    def requires_approval(self, risk_level: RiskLevel) -> bool:
        """
        Check if risk level requires human approval.
        
        Args:
            risk_level: The assessed risk level
        
        Returns:
            True if approval is required, False for auto-approve
        """
        return not self.rules["risk_levels"][risk_level].get("auto_approve", False)
    
    def get_approvers(self, risk_level: RiskLevel) -> List[str]:
        """
        Get list of roles that can approve this risk level.
        
        Args:
            risk_level: The assessed risk level
        
        Returns:
            List of role names (e.g., ["team_lead", "tech_lead"])
        """
        return self.rules["risk_levels"][risk_level].get("approvers", [])
    
    def get_timeout_minutes(self, risk_level: RiskLevel) -> int:
        """Get approval timeout in minutes for risk level"""
        return self.rules["risk_levels"][risk_level].get("timeout_minutes", 30)
    
    def requires_justification(self, risk_level: RiskLevel) -> bool:
        """Check if risk level requires justification for approval"""
        return self.rules["risk_levels"][risk_level].get("require_justification", False)
    
    def get_notification_channels(self, risk_level: RiskLevel) -> List[str]:
        """Get notification channels for risk level"""
        return self.rules.get("notification_channels", {}).get(risk_level, ["log"])


# Singleton instance
_risk_assessor_instance: Optional[RiskAssessor] = None


def get_risk_assessor(config_path: Optional[str] = None) -> RiskAssessor:
    """Get or create RiskAssessor singleton instance"""
    global _risk_assessor_instance
    if _risk_assessor_instance is None:
        _risk_assessor_instance = RiskAssessor(config_path)
    return _risk_assessor_instance
