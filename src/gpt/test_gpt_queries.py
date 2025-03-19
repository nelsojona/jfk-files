#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT Query Testing Tool for JFK Files

This script tests the functionality of the custom GPT configuration
with sample queries to ensure proper knowledge retrieval.

Version: 1.0.0
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_gpt_queries')

# Load environment variables from .env file
load_dotenv()

# API configuration - get API key from environment or argument
API_KEY = os.getenv("OPENAI_API_KEY", "")

# Test queries for the JFK Files GPT
SAMPLE_QUERIES = [
    "What is document 104-10003-10041 about?",
    "Find information about Lee Harvey Oswald's trip to Mexico City",
    "What evidence was found at the scene of the JFK assassination?",
    "Who was Jack Ruby and what was his role?",
    "Tell me about CIA involvement in the JFK assassination investigation",
    "What was the Warren Commission?",
    "Find documents related to the Zapruder film",
    "What evidence of conspiracy exists in the JFK files?",
    "Show me information about the magic bullet theory",
    "What did witnesses at Dealey Plaza report seeing?"
]

def run_gpt_query(query, api_key=None, gpt_id=None, max_tokens=1000, temperature=0.7):
    """
    Run a query against the custom GPT using the OpenAI API.
    
    Args:
        query (str): The query to run
        api_key (str): OpenAI API key (overrides environment variable)
        gpt_id (str): The GPT ID to use
        max_tokens (int): Maximum tokens in the response
        temperature (float): Temperature for response generation (0.0-1.0)
    
    Returns:
        dict: The API response or None if there was an error
    """
    # Use provided API key or fallback to environment variable
    key = api_key or API_KEY
    
    if not key:
        logger.error("No API key provided. Set OPENAI_API_KEY in .env file or provide via --api-key")
        return None
    
    # OpenAI API endpoint for GPT queries
    # NOTE: Using environment variable for base URL to support potential non-standard deployments
    api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    endpoint = f"{api_base}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    
    # Prepare the query payload
    payload = {
        "model": gpt_id or "gpt-4",  # Fallback to gpt-4 if no specific GPT ID
        "messages": [
            {"role": "system", "content": "You are a helpful assistant with access to JFK Files knowledge."},
            {"role": "user", "content": query}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    try:
        logger.info(f"Sending query: {query}")
        
        # Add request timing
        start_time = time.time()
        response = requests.post(endpoint, headers=headers, json=payload)
        response_time = time.time() - start_time
        
        response.raise_for_status()
        result = response.json()
        
        # Extract the response content
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Log basic stats
        logger.info(f"Response received in {response_time:.2f}s, {len(content)} chars")
        
        return {
            "query": query,
            "response": content,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
            "tokens": result.get("usage", {})
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        if hasattr(e, 'response'):
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error running query: {e}")
        return None

def test_queries(queries=None, api_key=None, gpt_id=None, output_file=None):
    """
    Test a list of queries against the GPT and save results.
    
    Args:
        queries (list): List of queries to test
        api_key (str): OpenAI API key
        gpt_id (str): The GPT ID to use
        output_file (str): File to save results to
    
    Returns:
        dict: Test results
    """
    queries = queries or SAMPLE_QUERIES
    
    results = {
        "metadata": {
            "test_date": datetime.now().isoformat(),
            "gpt_id": gpt_id or "default",
            "queries_count": len(queries)
        },
        "results": []
    }
    
    # Run each query
    for i, query in enumerate(queries):
        logger.info(f"Testing query {i+1}/{len(queries)}: {query}")
        
        result = run_gpt_query(query, api_key, gpt_id)
        
        if result:
            results["results"].append(result)
            
            # Print a snippet of the response
            response_snippet = result["response"][:100] + "..." if len(result["response"]) > 100 else result["response"]
            logger.info(f"Response snippet: {response_snippet}")
        else:
            logger.error(f"Query failed: {query}")
            results["results"].append({
                "query": query,
                "error": "Query failed",
                "timestamp": datetime.now().isoformat()
            })
        
        # Add a small delay between queries to avoid rate limiting
        time.sleep(1)
    
    # Calculate summary statistics
    successful_queries = sum(1 for r in results["results"] if "error" not in r)
    
    results["summary"] = {
        "total_queries": len(queries),
        "successful_queries": successful_queries,
        "success_rate": successful_queries / len(queries) if queries else 0,
        "average_response_time": sum(r.get("response_time", 0) for r in results["results"] if "response_time" in r) / successful_queries if successful_queries else 0
    }
    
    # Save results if output file specified
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    return results

def main():
    """
    Main function to parse arguments and run query tests.
    """
    parser = argparse.ArgumentParser(description="Test GPT queries for JFK Files")
    parser.add_argument("--api-key", help="OpenAI API key (overrides environment variable)")
    parser.add_argument("--gpt-id", help="Custom GPT ID to use")
    parser.add_argument("--query", help="Single query to test")
    parser.add_argument("--queries-file", help="JSON file with list of queries to test")
    parser.add_argument("--output-file", default="test_results.json", help="File to save results to")
    
    args = parser.parse_args()
    
    # Load custom queries if provided
    queries = SAMPLE_QUERIES
    
    if args.query:
        # Single query mode
        queries = [args.query]
    elif args.queries_file:
        # Load queries from file
        try:
            with open(args.queries_file, 'r', encoding='utf-8') as f:
                file_content = json.load(f)
                if isinstance(file_content, list):
                    queries = file_content
                elif isinstance(file_content, dict) and "queries" in file_content:
                    queries = file_content["queries"]
                else:
                    logger.error(f"Invalid queries file format: {args.queries_file}")
                    return 1
                
            logger.info(f"Loaded {len(queries)} queries from {args.queries_file}")
        except Exception as e:
            logger.error(f"Error loading queries file: {e}")
            return 1
    
    # Run the tests
    results = test_queries(
        queries=queries,
        api_key=args.api_key,
        gpt_id=args.gpt_id,
        output_file=args.output_file
    )
    
    # Print summary
    logger.info("Test summary:")
    logger.info(f"Total queries: {results['summary']['total_queries']}")
    logger.info(f"Successful queries: {results['summary']['successful_queries']}")
    logger.info(f"Success rate: {results['summary']['success_rate'] * 100:.1f}%")
    logger.info(f"Average response time: {results['summary']['average_response_time']:.2f}s")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())