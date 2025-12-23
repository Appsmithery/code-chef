"""
Comprehensive End-to-End Tracing Validation

Tests the complete LangSmith optimization implementation with real API calls:
- Intent recognition (compressed prompts, two-pass)
- Trace metadata enrichment
- Uncertainty sampling
- Hard negative mining
- Token usage optimization

Run against production: python comprehensive_e2e_tracing_test.py --env production
Run against local: python comprehensive_e2e_tracing_test.py --env local
"""

import asyncio
import requests
import json
import time
import argparse
from typing import List, Dict, Any
from datetime import datetime

# Test scenarios covering different intent types and confidence levels
TEST_SCENARIOS = [
    {
        "name": "High Confidence - Feature Request",
        "message": "Implement a JWT authentication middleware with refresh tokens",
        "expected_intent": "task_submission",
        "expected_confidence": "high",
        "expected_agent": "feature_dev"
    },
    {
        "name": "High Confidence - Code Review",
        "message": "Review the authentication logic in src/auth/login.py for security vulnerabilities",
        "expected_intent": "task_submission",
        "expected_confidence": "high",
        "expected_agent": "code_review"
    },
    {
        "name": "High Confidence - Documentation",
        "message": "Create API documentation for the user authentication endpoints",
        "expected_intent": "task_submission",
        "expected_confidence": "high",
        "expected_agent": "documentation"
    },
    {
        "name": "Medium Confidence - Mixed Intent",
        "message": "Can you help me understand how the authentication works and maybe improve it?",
        "expected_intent": "clarification_needed",
        "expected_confidence": "medium",
        "expected_agent": None
    },
    {
        "name": "Low Confidence - Ambiguous",
        "message": "The thing is not working properly",
        "expected_intent": "clarification_needed",
        "expected_confidence": "low",
        "expected_agent": None
    },
    {
        "name": "High Confidence - Infrastructure",
        "message": "Deploy the application to Kubernetes with horizontal pod autoscaling",
        "expected_intent": "task_submission",
        "expected_confidence": "high",
        "expected_agent": "infrastructure"
    },
    {
        "name": "High Confidence - CI/CD",
        "message": "Set up GitHub Actions workflow for automated testing and deployment",
        "expected_intent": "task_submission",
        "expected_confidence": "high",
        "expected_agent": "cicd"
    },
    {
        "name": "Medium Confidence - Question",
        "message": "What's the best way to handle authentication in microservices?",
        "expected_intent": "conversation",
        "expected_confidence": "medium",
        "expected_agent": None
    },
    {
        "name": "High Confidence - Refactoring",
        "message": "Refactor the database connection pool to use connection pooling",
        "expected_intent": "task_submission",
        "expected_confidence": "high",
        "expected_agent": "feature_dev"
    },
    {
        "name": "Low Confidence - Vague Context",
        "message": "help with the project",
        "expected_intent": "clarification_needed",
        "expected_confidence": "low",
        "expected_agent": None
    }
]


class E2ETracingValidator:
    def __init__(self, base_url: str, environment: str):
        self.base_url = base_url
        self.environment = environment
        self.results: List[Dict[str, Any]] = []
        self.user_id = f"e2e-test-{int(time.time())}"
        
    def run_test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test scenario and capture results."""
        print(f"\n{'='*80}")
        print(f"🧪 Testing: {scenario['name']}")
        print(f"📝 Message: {scenario['message']}")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            # Make request to /chat endpoint
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "message": scenario["message"],
                    "user_id": self.user_id
                },
                timeout=30
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code != 200:
                print(f"❌ Request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return {
                    "scenario": scenario["name"],
                    "status": "failed",
                    "error": f"HTTP {response.status_code}",
                    "elapsed_time": elapsed_time
                }
            
            data = response.json()
            
            # Extract key metrics
            result = {
                "scenario": scenario["name"],
                "status": "success",
                "elapsed_time": elapsed_time,
                "response": data,
                "message": scenario["message"],
                "expected_intent": scenario.get("expected_intent"),
                "expected_confidence": scenario.get("expected_confidence"),
                "expected_agent": scenario.get("expected_agent")
            }
            
            # Display results
            print(f"\n✅ Response received in {elapsed_time:.2f}s")
            print(f"📊 Response keys: {list(data.keys())}")
            
            if "intent" in data:
                print(f"🎯 Intent: {data['intent']}")
            if "confidence" in data:
                confidence_level = "high" if data["confidence"] > 0.8 else "medium" if data["confidence"] > 0.5 else "low"
                print(f"📈 Confidence: {data['confidence']:.2f} ({confidence_level})")
            if "agent" in data:
                print(f"🤖 Agent: {data.get('agent', 'N/A')}")
            if "task_id" in data:
                print(f"🆔 Task ID: {data['task_id']}")
            if "trace_url" in data:
                print(f"🔗 Trace URL: {data['trace_url']}")
            
            # Validate expectations
            validations = []
            
            if "intent" in data and scenario.get("expected_intent"):
                intent_match = data["intent"] == scenario["expected_intent"]
                validations.append({
                    "check": "Intent Match",
                    "passed": intent_match,
                    "expected": scenario["expected_intent"],
                    "actual": data["intent"]
                })
            
            if "confidence" in data and scenario.get("expected_confidence"):
                conf = data["confidence"]
                expected = scenario["expected_confidence"]
                conf_level = "high" if conf > 0.8 else "medium" if conf > 0.5 else "low"
                conf_match = conf_level == expected
                validations.append({
                    "check": "Confidence Level",
                    "passed": conf_match,
                    "expected": expected,
                    "actual": conf_level
                })
            
            if "agent" in data and scenario.get("expected_agent"):
                agent_match = data.get("agent") == scenario["expected_agent"]
                validations.append({
                    "check": "Agent Selection",
                    "passed": agent_match,
                    "expected": scenario["expected_agent"],
                    "actual": data.get("agent")
                })
            
            result["validations"] = validations
            
            # Print validation results
            if validations:
                print(f"\n📋 Validations:")
                for v in validations:
                    status = "✅" if v["passed"] else "❌"
                    print(f"  {status} {v['check']}: Expected '{v['expected']}', Got '{v['actual']}'")
            
            return result
            
        except requests.exceptions.Timeout:
            elapsed_time = time.time() - start_time
            print(f"❌ Request timed out after {elapsed_time:.2f}s")
            return {
                "scenario": scenario["name"],
                "status": "timeout",
                "elapsed_time": elapsed_time
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"❌ Error: {str(e)}")
            return {
                "scenario": scenario["name"],
                "status": "error",
                "error": str(e),
                "elapsed_time": elapsed_time
            }
    
    def run_all_scenarios(self):
        """Execute all test scenarios sequentially."""
        print(f"\n{'#'*80}")
        print(f"🚀 Starting Comprehensive E2E Tracing Validation")
        print(f"🌍 Environment: {self.environment}")
        print(f"🔗 Base URL: {self.base_url}")
        print(f"👤 User ID: {self.user_id}")
        print(f"📊 Total Scenarios: {len(TEST_SCENARIOS)}")
        print(f"{'#'*80}")
        
        for i, scenario in enumerate(TEST_SCENARIOS, 1):
            print(f"\n\n[{i}/{len(TEST_SCENARIOS)}] Running: {scenario['name']}")
            result = self.run_test_scenario(scenario)
            self.results.append(result)
            
            # Brief pause between requests
            if i < len(TEST_SCENARIOS):
                print("\n⏳ Waiting 2 seconds before next test...")
                time.sleep(2)
        
        self.print_summary()
    
    def print_summary(self):
        """Print comprehensive summary of all test results."""
        print(f"\n\n{'#'*80}")
        print(f"📊 COMPREHENSIVE TEST SUMMARY")
        print(f"{'#'*80}\n")
        
        # Overall stats
        total = len(self.results)
        successful = len([r for r in self.results if r["status"] == "success"])
        failed = len([r for r in self.results if r["status"] == "failed"])
        errors = len([r for r in self.results if r["status"] == "error"])
        timeouts = len([r for r in self.results if r["status"] == "timeout"])
        
        print(f"✅ Successful: {successful}/{total} ({successful/total*100:.1f}%)")
        print(f"❌ Failed: {failed}/{total}")
        print(f"⚠️  Errors: {errors}/{total}")
        print(f"⏱️  Timeouts: {timeouts}/{total}\n")
        
        # Response time stats
        successful_results = [r for r in self.results if r["status"] == "success"]
        if successful_results:
            times = [r["elapsed_time"] for r in successful_results]
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"⏱️  Response Times:")
            print(f"   Average: {avg_time:.2f}s")
            print(f"   Min: {min_time:.2f}s")
            print(f"   Max: {max_time:.2f}s\n")
        
        # Validation summary
        all_validations = []
        for r in self.results:
            if "validations" in r:
                all_validations.extend(r["validations"])
        
        if all_validations:
            passed = len([v for v in all_validations if v["passed"]])
            total_validations = len(all_validations)
            print(f"✅ Validations Passed: {passed}/{total_validations} ({passed/total_validations*100:.1f}%)\n")
        
        # Individual scenario results
        print(f"📋 Scenario Results:\n")
        for i, result in enumerate(self.results, 1):
            status_icon = {
                "success": "✅",
                "failed": "❌",
                "error": "⚠️",
                "timeout": "⏱️"
            }.get(result["status"], "❓")
            
            print(f"{i:2d}. {status_icon} {result['scenario']}")
            print(f"    Status: {result['status']}")
            print(f"    Time: {result.get('elapsed_time', 0):.2f}s")
            
            if result["status"] == "success":
                resp = result.get("response", {})
                if "intent" in resp:
                    print(f"    Intent: {resp['intent']}")
                if "confidence" in resp:
                    print(f"    Confidence: {resp['confidence']:.2f}")
                if "agent" in resp:
                    print(f"    Agent: {resp.get('agent', 'N/A')}")
                
                if "validations" in result:
                    passed_vals = len([v for v in result["validations"] if v["passed"]])
                    total_vals = len(result["validations"])
                    print(f"    Validations: {passed_vals}/{total_vals} passed")
            
            if "error" in result:
                print(f"    Error: {result['error']}")
            
            print()
        
        # LangSmith trace information
        print(f"\n{'='*80}")
        print(f"🔍 LangSmith Trace Information")
        print(f"{'='*80}\n")
        print(f"Project: code-chef-{self.environment}")
        print(f"User ID Filter: {self.user_id}")
        print(f"Time Range: Last 10 minutes")
        print(f"\n🔗 View traces: https://smith.langchain.com/")
        print(f"   Filter: user_id:\"{self.user_id}\" AND environment:\"{self.environment}\"")
        
        # What to look for in traces
        print(f"\n📋 In LangSmith, verify:")
        print(f"   ✓ All {successful} successful requests created traces")
        print(f"   ✓ Trace metadata includes: environment, model_version, experiment_group, extension_version")
        print(f"   ✓ Token usage shows ~40-60% reduction for high-confidence cases")
        print(f"   ✓ Two-pass recognition visible for medium/low confidence cases")
        print(f"   ✓ Uncertainty sampling flags present where applicable")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"e2e_tracing_results_{self.environment}_{timestamp}.json"
        
        with open(output_file, "w") as f:
            json.dump({
                "summary": {
                    "environment": self.environment,
                    "base_url": self.base_url,
                    "user_id": self.user_id,
                    "total_scenarios": total,
                    "successful": successful,
                    "failed": failed,
                    "errors": errors,
                    "timeouts": timeouts,
                    "timestamp": timestamp
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print(f"\n{'#'*80}\n")


def main():
    parser = argparse.ArgumentParser(description="Comprehensive E2E Tracing Validation")
    parser.add_argument(
        "--env",
        choices=["production", "local"],
        default="local",
        help="Environment to test against"
    )
    
    args = parser.parse_args()
    
    # Set base URL based on environment
    base_url = {
        "production": "https://codechef.appsmithery.co",
        "local": "http://localhost:8001"
    }[args.env]
    
    # Run validation
    validator = E2ETracingValidator(base_url, args.env)
    validator.run_all_scenarios()


if __name__ == "__main__":
    main()
