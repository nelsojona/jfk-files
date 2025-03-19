#!/usr/bin/env python3
"""
Refine GPT Instructions Based on Test Results

This script analyzes GPT test results and suggests improvements to the system message
and other GPT configuration settings based on test performance.
"""

import json
import os
import argparse
import datetime
from typing import Dict, List, Any, Optional

class InstructionRefiner:
    """Analyzes test results and suggests GPT instruction improvements."""
    
    def __init__(self, gpt_config_path: str, test_results_path: str):
        """
        Initialize the refiner with paths to GPT config and test results.
        
        Args:
            gpt_config_path: Path to GPT configuration JSON
            test_results_path: Path to test results JSON
        """
        self.gpt_config_path = gpt_config_path
        self.test_results_path = test_results_path
        
        # Load the configuration and test results
        self.config = self._load_json(gpt_config_path)
        self.test_results = self._load_json(test_results_path)
    
    def _load_json(self, file_path: str) -> Dict:
        """Load JSON data from a file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_test_results(self) -> Dict[str, Any]:
        """
        Analyze test results to identify patterns in failures.
        
        Returns:
            Dictionary with analysis results
        """
        results = self.test_results.get("results", [])
        
        # Group results by category
        categories = {}
        for result in results:
            category = result.get("category", "General")
            if category not in categories:
                categories[category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "failed_tests": []
                }
            
            categories[category]["total"] += 1
            
            if result.get("success", False):
                categories[category]["passed"] += 1
            else:
                categories[category]["failed"] += 1
                categories[category]["failed_tests"].append(result)
        
        # Identify common failure patterns
        failure_patterns = self._identify_failure_patterns(results)
        
        return {
            "categories": categories,
            "failure_patterns": failure_patterns,
            "total_tests": len(results),
            "passed_tests": sum(1 for r in results if r.get("success", False)),
            "failed_tests": sum(1 for r in results if not r.get("success", False))
        }
    
    def _identify_failure_patterns(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common patterns in failed tests."""
        # Filter failed tests
        failed_tests = [r for r in results if not r.get("success", False)]
        
        patterns = []
        
        # Check for failure to cite document IDs
        cite_failures = []
        for test in failed_tests:
            if any(b.get("description", "").lower().find("cite") >= 0 for b in test.get("behavior_results", [])):
                cite_failures.append(test)
        
        if cite_failures:
            patterns.append({
                "name": "citation_missing",
                "description": "Failure to cite document IDs when providing information",
                "affected_tests": len(cite_failures),
                "examples": cite_failures[:2]  # First two examples
            })
        
        # Check for irrelevant information
        irrelevant_info = []
        for test in failed_tests:
            if any(b.get("type") == "not_contains" and not b.get("result", True) for b in test.get("behavior_results", [])):
                irrelevant_info.append(test)
        
        if irrelevant_info:
            patterns.append({
                "name": "irrelevant_information",
                "description": "Providing irrelevant or fabricated information not in the knowledge base",
                "affected_tests": len(irrelevant_info),
                "examples": irrelevant_info[:2]
            })
        
        # Check for missing key topics
        missing_topics = []
        for test in failed_tests:
            if any(b.get("type") == "contains" and not b.get("result", True) for b in test.get("behavior_results", [])):
                missing_topics.append(test)
        
        if missing_topics:
            patterns.append({
                "name": "missing_topics",
                "description": "Failing to mention key topics requested in the query",
                "affected_tests": len(missing_topics),
                "examples": missing_topics[:2]
            })
        
        return patterns
    
    def suggest_improvements(self) -> Dict[str, Any]:
        """
        Suggest improvements to GPT configuration based on test analysis.
        
        Returns:
            Dictionary with improvement suggestions
        """
        analysis = self.analyze_test_results()
        
        # Original system message
        original_system_message = self.config.get("system_message", "")
        
        # Suggestions for each failure pattern
        suggestions = []
        for pattern in analysis["failure_patterns"]:
            if pattern["name"] == "citation_missing":
                suggestions.append({
                    "target": "system_message",
                    "issue": "Insufficient emphasis on document citation",
                    "suggestion": "Strengthen instructions to always cite document IDs when providing information",
                    "example_addition": (
                        "IMPORTANT: ALWAYS cite specific document IDs (e.g., 104-10004-10143) "
                        "when providing information from the JFK Files. If multiple documents "
                        "support a statement, cite all relevant documents."
                    )
                })
            
            elif pattern["name"] == "irrelevant_information":
                suggestions.append({
                    "target": "system_message",
                    "issue": "Providing information not in the knowledge base",
                    "suggestion": "Emphasize to only provide information that exists in the knowledge base",
                    "example_addition": (
                        "You must ONLY provide information that exists in the JFK Files knowledge base. "
                        "Do not make up or infer information that is not explicitly stated in the documents. "
                        "When asked about topics not covered in the JFK Files, clearly state that the "
                        "information is not available in your knowledge base."
                    )
                })
            
            elif pattern["name"] == "missing_topics":
                suggestions.append({
                    "target": "system_message",
                    "issue": "Not addressing key topics in queries",
                    "suggestion": "Improve instructions to ensure all parts of complex queries are addressed",
                    "example_addition": (
                        "When responding to queries with multiple parts or topics, ensure you address EACH part "
                        "of the query. For complex questions mentioning multiple entities, people, or events, "
                        "provide information about each one and any connections between them found in the documents."
                    )
                })
        
        # Check for category-specific issues
        category_issues = []
        for category, stats in analysis["categories"].items():
            if stats["failed"] > 0 and (stats["failed"] / stats["total"]) > 0.5:
                category_issues.append({
                    "category": category,
                    "failure_rate": stats["failed"] / stats["total"],
                    "examples": stats["failed_tests"][:1]  # First example
                })
        
        # Add category-specific suggestions
        for issue in category_issues:
            if issue["category"] == "Document Retrieval":
                suggestions.append({
                    "target": "system_message",
                    "issue": f"Poor performance in {issue['category']} queries",
                    "suggestion": "Improve document retrieval instructions",
                    "example_addition": (
                        "For document retrieval requests, provide a comprehensive summary of the document's "
                        "content. Include metadata such as document date, agency origin, and subject matter. "
                        "Quote key passages verbatim and clearly differentiate between direct quotes and your summaries."
                    )
                })
            
            elif issue["category"] == "Cross-Document Analysis":
                suggestions.append({
                    "target": "system_message",
                    "issue": f"Poor performance in {issue['category']} queries",
                    "suggestion": "Enhance instructions for cross-document analysis",
                    "example_addition": (
                        "When asked to compare or analyze multiple documents, identify both similarities and "
                        "differences in content, context, and significance. Highlight connections between "
                        "documents including references to the same people, events, or organizations. "
                        "Organize your response with clear headings for each document and comparison points."
                    )
                })
        
        # Generate improved system message
        improved_system_message = original_system_message
        
        # Add suggested improvements to the system message
        for suggestion in suggestions:
            if suggestion["target"] == "system_message":
                if suggestion["example_addition"] not in improved_system_message:
                    improved_system_message += f"\n\n{suggestion['example_addition']}"
        
        return {
            "original_system_message": original_system_message,
            "improved_system_message": improved_system_message,
            "suggestions": suggestions,
            "analysis": analysis
        }
    
    def save_refined_config(self, output_path: Optional[str] = None) -> str:
        """
        Save the refined GPT configuration.
        
        Args:
            output_path: Optional path to save the refined config (defaults to original path with timestamp)
        
        Returns:
            Path to the saved configuration file
        """
        improvements = self.suggest_improvements()
        
        # Create a copy of the original config
        refined_config = self.config.copy()
        
        # Update the system message
        refined_config["system_message"] = improvements["improved_system_message"]
        
        # Add refinement metadata
        refined_config["refinement_info"] = {
            "refined_at": datetime.datetime.now().isoformat(),
            "based_on_test_results": self.test_results_path,
            "suggestions_applied": [s["issue"] for s in improvements["suggestions"]]
        }
        
        # Determine output path
        if not output_path:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, ext = os.path.splitext(self.gpt_config_path)
            output_path = f"{filename}_refined_{timestamp}{ext}"
        
        # Save the refined config
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(refined_config, f, indent=2)
        
        return output_path
    
    def generate_report(self, output_dir: str = "gpt_refinements") -> str:
        """
        Generate a detailed report of the refinement process.
        
        Args:
            output_dir: Directory to save the report
        
        Returns:
            Path to the generated report
        """
        os.makedirs(output_dir, exist_ok=True)
        
        improvements = self.suggest_improvements()
        analysis = improvements["analysis"]
        
        # Create report filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"refinement_report_{timestamp}.md")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# GPT Instruction Refinement Report\n\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Test Results Summary\n\n")
            f.write(f"Total Tests: {analysis['total_tests']}\n")
            f.write(f"Passed: {analysis['passed_tests']}\n")
            f.write(f"Failed: {analysis['failed_tests']}\n")
            f.write(f"Pass Rate: {(analysis['passed_tests'] / analysis['total_tests']) * 100:.1f}%\n\n")
            
            f.write("### Performance by Category\n\n")
            f.write("| Category | Total | Passed | Failed | Pass Rate |\n")
            f.write("|----------|-------|--------|--------|----------|\n")
            
            for category, stats in analysis["categories"].items():
                pass_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
                f.write(f"| {category} | {stats['total']} | {stats['passed']} | {stats['failed']} | {pass_rate:.1f}% |\n")
            
            f.write("\n## Identified Issues\n\n")
            
            if not analysis["failure_patterns"]:
                f.write("No significant failure patterns identified.\n\n")
            else:
                for i, pattern in enumerate(analysis["failure_patterns"], 1):
                    f.write(f"### Issue {i}: {pattern['description']}\n\n")
                    f.write(f"Affected Tests: {pattern['affected_tests']}\n\n")
                    
                    if pattern.get("examples"):
                        f.write("Example Failed Test:\n")
                        example = pattern["examples"][0]
                        f.write(f"- Test ID: {example.get('test_id', 'Unknown')}\n")
                        f.write(f"- Category: {example.get('category', 'Unknown')}\n")
                        f.write(f"- Query: {example.get('query', 'Unknown')}\n\n")
            
            f.write("## Suggested Improvements\n\n")
            
            if not improvements["suggestions"]:
                f.write("No improvements suggested.\n\n")
            else:
                for i, suggestion in enumerate(improvements["suggestions"], 1):
                    f.write(f"### Suggestion {i}: {suggestion['suggestion']}\n\n")
                    f.write(f"Issue: {suggestion['issue']}\n\n")
                    
                    if "example_addition" in suggestion:
                        f.write("Recommended Addition:\n```\n")
                        f.write(suggestion["example_addition"])
                        f.write("\n```\n\n")
            
            f.write("## System Message Changes\n\n")
            
            f.write("### Original System Message\n\n```\n")
            f.write(improvements["original_system_message"])
            f.write("\n```\n\n")
            
            f.write("### Refined System Message\n\n```\n")
            f.write(improvements["improved_system_message"])
            f.write("\n```\n\n")
            
            f.write("## Next Steps\n\n")
            f.write("1. Review the suggested improvements and refine further if needed\n")
            f.write("2. Update the GPT configuration with the refined system message\n")
            f.write("3. Re-run the tests to verify performance improvements\n")
            f.write("4. Iterate if necessary until desired performance is achieved\n")
        
        print(f"Report saved to: {report_file}")
        return report_file

def main():
    parser = argparse.ArgumentParser(description="Refine GPT instructions based on test results")
    parser.add_argument(
        "--config",
        default="lite_llm/gpt_configuration.json",
        help="Path to the GPT configuration JSON file"
    )
    parser.add_argument(
        "--test-results",
        required=True,
        help="Path to the test results JSON file"
    )
    parser.add_argument(
        "--output-dir",
        default="gpt_refinements",
        help="Directory to save the refinement report and refined configuration"
    )
    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save the refined configuration"
    )
    parser.add_argument(
        "--output-config",
        help="Path to save the refined configuration (if --save-config is used)"
    )
    
    args = parser.parse_args()
    
    try:
        refiner = InstructionRefiner(args.config, args.test_results)
        
        # Generate report
        report_file = refiner.generate_report(args.output_dir)
        
        # Save refined configuration if requested
        if args.save_config:
            output_path = refiner.save_refined_config(args.output_config)
            print(f"Refined configuration saved to: {output_path}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
