#!/usr/bin/env python3
"""
Comprehensive integration test script for the Enhanced Singapore Housing Assistant.
Validates core functionality, RAG system, agent orchestration, and error handling.
"""

import sys
import os
import time

# Add the project root to the system path to allow for imports
# Assuming the script is run from the project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_tests():
    """
    Runs a series of tests to validate the system's integration and workflows.
    """
    print("🧪 Starting Comprehensive Integration Tests...")
    all_tests_passed = True

    try:
        from agents.orchestrator_agent import orchestrator
        print("✅ Orchestrator agent imported successfully.")
    except ImportError as e:
        print(f"❌ Failed to import orchestrator agent: {e}")
        return False
    
    # --------------------------------------------------------------------------
    # Test Case 1: RAG System and Basic Orchestration
    # --------------------------------------------------------------------------
    print("\n--- Test Case 1: Basic RAG and Agent Orchestration ---")
    try:
        query = "I'm a Singapore citizen looking for housing grants"
        print(f"Running test query: '{query}'")
        
        # It's good practice to ensure all dependencies are initialized before testing.
        from tools import initialize_rag_system
        rag_status = initialize_rag_system()
        print(f"✅ RAG System: {rag_status}")
        
        response = orchestrator(query)
        
        # We handle the various return types of the agent call
        final_response_text = str(response.content if hasattr(response, 'content') else response)
        
        # Validate that the response contains relevant keywords
        if "grant" in final_response_text.lower() and "citizen" in final_response_text.lower():
            print("✅ RAG and orchestration test passed: The response is relevant and correct.")
        else:
            print(f"❌ RAG and orchestration test failed. The response was not as expected: {final_response_text}")
            all_tests_passed = False
            
    except Exception as e:
        print(f"❌ Test Case 1 failed. An unhandled exception occurred: {e}")
        all_tests_passed = False

    # --------------------------------------------------------------------------
    # Test Case 2: Financial Calculation Workflow
    # --------------------------------------------------------------------------
    print("\n--- Test Case 2: Financial Calculation Workflow ---")
    try:
        query = "What is the estimated budget for a 5000 monthly income and 1000 in existing debt?"
        print(f"Running test query for financial calculation: '{query}'")
        response = orchestrator(query)
        
        # Again, handle different response formats and check for expected output
        final_response_text = str(response.content if hasattr(response, 'content') else response)
        
        if "$576,000" in final_response_text or "576000" in final_response_text:
            print("✅ Financial calculation test passed: Correct budget range estimated.")
        else:
            print(f"❌ Financial calculation test failed. Response was: {final_response_text}")
            all_tests_passed = False
            
    except Exception as e:
        print(f"❌ Test Case 2 failed. An unhandled exception occurred: {e}")
        all_tests_passed = False

    # --------------------------------------------------------------------------
    # Test Case 3: Error Handling and Graceful Failure
    # --------------------------------------------------------------------------
    print("\n--- Test Case 3: Graceful Error Handling ---")
    try:
        query = "Tell me about the latest stock market news in the US."
        print(f"Running test query for an out-of-scope question: '{query}'")
        response = orchestrator(query)
        
        final_response_text = str(response.content if hasattr(response, 'content') else response)

        if "out of my scope" in final_response_text.lower() or "cannot assist" in final_response_text.lower() or "focus on singapore housing" in final_response_text.lower():
            print("✅ Graceful failure handled successfully.")
        else:
            print(f"❌ Failure to gracefully handle out-of-scope query. Response was: {final_response_text}")
            all_tests_passed = False
            
    except Exception as e:
        print(f"❌ Test Case 3 failed. An unhandled exception occurred: {e}")
        all_tests_passed = False

    # --------------------------------------------------------------------------
    # Final Result
    # --------------------------------------------------------------------------
    
    if all_tests_passed:
        print("\n✅ All comprehensive integration tests passed successfully!")
        return True
    else:
        print("\n❌ One or more integration tests failed. Please review the output.")
        return False

if __name__ == "__main__":
    if run_tests():
        sys.exit(0)  # Exit with success code
    else:
        sys.exit(1)  # Exit with failure code