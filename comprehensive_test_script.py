# test_aws_rag.py - Comprehensive AWS RAG Integration Test

import os
import sys
import boto3
import json
import time
from datetime import datetime
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class AWSRAGTester:
    """Comprehensive tester for AWS Knowledge Base RAG integration"""
    
    def __init__(self):
        self.test_results = {
            'aws_connectivity': False,
            'knowledge_base_access': False,
            'document_retrieval': False,
            'end_to_end_query': False,
            'performance_metrics': {},
            'error_details': []
        }
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        self.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID')
        self.s3_bucket = os.getenv('S3_BUCKET_NAME')
        self.region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        logger.info("AWS RAG Integration Test Suite Initialized")
        logger.info(f"Knowledge Base ID: {self.knowledge_base_id}")
        logger.info(f"S3 Bucket: {self.s3_bucket}")
        logger.info(f"Region: {self.region}")
    
    def test_1_aws_connectivity(self) -> bool:
        """Test 1: Verify AWS credentials and basic connectivity"""
        logger.info("\n=== TEST 1: AWS Connectivity ===")
        
        try:
            # Test AWS credentials
            sts_client = boto3.client('sts', region_name=self.region)
            identity = sts_client.get_caller_identity()
            
            account_id = identity.get('Account')
            user_arn = identity.get('Arn')
            
            logger.info(f"✓ AWS Authentication successful")
            logger.info(f"  Account ID: {account_id}")
            logger.info(f"  User/Role: {user_arn}")
            
            # Test S3 access
            s3_client = boto3.client('s3', region_name=self.region)
            s3_client.list_buckets()
            logger.info("✓ S3 access confirmed")
            
            # Test Bedrock access
            bedrock_client = boto3.client('bedrock', region_name=self.region)
            bedrock_client.list_foundation_models()
            logger.info("✓ Bedrock access confirmed")
            
            # Test Bedrock Agent Runtime access
            bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=self.region)
            logger.info("✓ Bedrock Agent Runtime client initialized")
            
            self.test_results['aws_connectivity'] = True
            return True
            
        except NoCredentialsError:
            error_msg = "AWS credentials not found. Run 'aws configure' or set environment variables."
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = f"AWS API Error ({error_code}): {str(e)}"
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Unexpected AWS connectivity error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
    
    def test_2_knowledge_base_access(self) -> bool:
        """Test 2: Verify Knowledge Base exists and is accessible"""
        logger.info("\n=== TEST 2: Knowledge Base Access ===")
        
        if not self.knowledge_base_id:
            error_msg = "KNOWLEDGE_BASE_ID not set in environment variables"
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
        
        try:
            bedrock_agent = boto3.client('bedrock-agent', region_name=self.region)
            
            # Get Knowledge Base details
            response = bedrock_agent.get_knowledge_base(
                knowledgeBaseId=self.knowledge_base_id
            )
            
            kb_info = response.get('knowledgeBase', {})
            kb_name = kb_info.get('name', 'Unknown')
            kb_status = kb_info.get('status', 'Unknown')
            
            logger.info(f"✓ Knowledge Base found: {kb_name}")
            logger.info(f"  Status: {kb_status}")
            logger.info(f"  ID: {self.knowledge_base_id}")
            
            # Check if Knowledge Base is ready
            if kb_status != 'ACTIVE':
                warning_msg = f"Knowledge Base status is {kb_status}, not ACTIVE. May affect testing."
                logger.warning(f"⚠ {warning_msg}")
                self.test_results['error_details'].append(warning_msg)
            
            # List data sources
            data_sources = bedrock_agent.list_data_sources(
                knowledgeBaseId=self.knowledge_base_id
            )
            
            ds_count = len(data_sources.get('dataSourceSummaries', []))
            logger.info(f"✓ Found {ds_count} data source(s)")
            
            for ds in data_sources.get('dataSourceSummaries', []):
                ds_name = ds.get('name', 'Unknown')
                ds_status = ds.get('status', 'Unknown')
                logger.info(f"  Data Source: {ds_name} (Status: {ds_status})")
            
            self.test_results['knowledge_base_access'] = True
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ResourceNotFoundException':
                error_msg = f"Knowledge Base {self.knowledge_base_id} not found"
            else:
                error_msg = f"Knowledge Base access error ({error_code}): {str(e)}"
            
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Unexpected Knowledge Base error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
    
    def test_3_document_retrieval(self) -> bool:
        """Test 3: Test document retrieval without generation"""
        logger.info("\n=== TEST 3: Document Retrieval ===")
        
        test_queries = [
            "HDB eligibility requirements",
            "CPF housing grants",
            "BTO application process"
        ]
        
        try:
            bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=self.region)
            
            successful_retrievals = 0
            
            for query in test_queries:
                logger.info(f"\nTesting retrieval for: '{query}'")
                
                start_time = time.time()
                
                response = bedrock_runtime.retrieve(
                    knowledgeBaseId=self.knowledge_base_id,
                    retrievalQuery={'text': query},
                    retrievalConfiguration={
                        'vectorSearchConfiguration': {
                            'numberOfResults': 3
                        }
                    }
                )
                
                end_time = time.time()
                retrieval_time = end_time - start_time
                
                results = response.get('retrievalResults', [])
                
                if results:
                    logger.info(f"✓ Retrieved {len(results)} documents ({retrieval_time:.2f}s)")
                    
                    # Log first result details
                    first_result = results[0]
                    score = first_result.get('score', 0)
                    content_preview = first_result.get('content', {}).get('text', '')[:100] + "..."
                    
                    logger.info(f"  Top result score: {score:.3f}")
                    logger.info(f"  Content preview: {content_preview}")
                    
                    successful_retrievals += 1
                else:
                    logger.warning(f"⚠ No documents retrieved for: '{query}'")
            
            if successful_retrievals > 0:
                logger.info(f"\n✓ Document retrieval working: {successful_retrievals}/{len(test_queries)} queries successful")
                self.test_results['document_retrieval'] = True
                return True
            else:
                error_msg = "No documents could be retrieved for any test query"
                logger.error(f"✗ {error_msg}")
                self.test_results['error_details'].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Document retrieval error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
    
    def test_4_end_to_end_query(self) -> bool:
        """Test 4: Full end-to-end query with generation"""
        logger.info("\n=== TEST 4: End-to-End Query with Generation ===")
        
        test_questions = [
            "What grants am I eligible for as a first-time HDB buyer?",
            "What is the income limit for BTO applications?",
            "How long does the HDB resale process take?"
        ]
        
        try:
            bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=self.region)
            
            successful_queries = 0
            total_query_time = 0
            
            for question in test_questions:
                logger.info(f"\nTesting end-to-end query: '{question}'")
                
                start_time = time.time()
                
                response = bedrock_runtime.retrieve_and_generate(
                    input={'text': question},
                    retrieveAndGenerateConfiguration={
                        'type': 'KNOWLEDGE_BASE',
                        'knowledgeBaseConfiguration': {
                            'knowledgeBaseId': self.knowledge_base_id,
                            'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
                        }
                    }
                )
                
                end_time = time.time()
                query_time = end_time - start_time
                total_query_time += query_time
                
                # Extract response
                answer = response.get('output', {}).get('text', '')
                citations = response.get('citations', [])
                session_id = response.get('sessionId', '')
                
                if answer and len(answer.strip()) > 10:  # Basic validation
                    logger.info(f"✓ Query successful ({query_time:.2f}s)")
                    logger.info(f"  Answer length: {len(answer)} characters")
                    logger.info(f"  Citations: {len(citations)}")
                    logger.info(f"  Session ID: {session_id}")
                    
                    # Preview answer
                    answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
                    logger.info(f"  Answer preview: {answer_preview}")
                    
                    successful_queries += 1
                else:
                    logger.warning(f"⚠ Query returned empty or very short response for: '{question}'")
            
            avg_query_time = total_query_time / len(test_questions) if test_questions else 0
            
            if successful_queries > 0:
                logger.info(f"\n✓ End-to-end queries working: {successful_queries}/{len(test_questions)} successful")
                logger.info(f"✓ Average query time: {avg_query_time:.2f} seconds")
                
                self.test_results['end_to_end_query'] = True
                self.test_results['performance_metrics']['avg_query_time'] = avg_query_time
                self.test_results['performance_metrics']['successful_queries'] = successful_queries
                return True
            else:
                error_msg = "No end-to-end queries were successful"
                logger.error(f"✗ {error_msg}")
                self.test_results['error_details'].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"End-to-end query error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
    
    def test_5_integration_with_tools(self) -> bool:
        """Test 5: Test integration with your custom RAG tools"""
        logger.info("\n=== TEST 5: Integration with Custom Tools ===")
        
        try:
            # Try importing your custom tools
            from ragtool.aws_rag_tools import (
                validate_aws_rag_configuration,
                aws_rag_search,
                singapore_housing_aws_search
            )
            
            logger.info("✓ Custom RAG tools imported successfully")
            
            # Test validation function
            logger.info("\nTesting validation function...")
            validation_result = validate_aws_rag_configuration()
            logger.info(f"Validation result: {validation_result}")
            
            # Test search functions
            logger.info("\nTesting custom search functions...")
            test_query = "What are the BTO eligibility requirements?"
            
            search_result = singapore_housing_aws_search(test_query, "hdb_policies")
            
            if search_result and len(str(search_result).strip()) > 10:
                logger.info("✓ Custom search functions working")
                logger.info(f"  Result preview: {str(search_result)[:150]}...")
                return True
            else:
                error_msg = "Custom search functions returned empty results"
                logger.warning(f"⚠ {error_msg}")
                self.test_results['error_details'].append(error_msg)
                return False
                
        except ImportError as e:
            error_msg = f"Cannot import custom RAG tools: {str(e)}"
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Custom tools integration error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            self.test_results['error_details'].append(error_msg)
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        logger.info("=" * 60)
        logger.info("AWS RAG INTEGRATION TEST SUITE")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Run tests sequentially
        tests = [
            ("AWS Connectivity", self.test_1_aws_connectivity),
            ("Knowledge Base Access", self.test_2_knowledge_base_access),
            ("Document Retrieval", self.test_3_document_retrieval),
            ("End-to-End Query", self.test_4_end_to_end_query),
            ("Tools Integration", self.test_5_integration_with_tools)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_function in tests:
            try:
                if test_function():
                    passed_tests += 1
            except Exception as e:
                error_msg = f"Test '{test_name}' failed with exception: {str(e)}"
                logger.error(f"✗ {error_msg}")
                self.test_results['error_details'].append(error_msg)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Generate summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        logger.info(f"Tests passed: {passed_tests}/{total_tests}")
        logger.info(f"Total test time: {total_time:.2f} seconds")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED! Your AWS RAG integration is working correctly.")
            overall_status = "PASS"
        elif passed_tests >= 3:
            logger.info("⚠️ PARTIAL SUCCESS - Most tests passed, but some issues found.")
            overall_status = "PARTIAL"
        else:
            logger.info("❌ TESTS FAILED - Major issues found. Check configuration.")
            overall_status = "FAIL"
        
        # Add summary to results
        self.test_results.update({
            'overall_status': overall_status,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'test_duration': total_time,
            'timestamp': datetime.now().isoformat()
        })
        
        # Print recommendations
        self._print_recommendations()
        
        return self.test_results
    
    def _print_recommendations(self):
        """Print recommendations based on test results"""
        logger.info("\n" + "=" * 60)
        logger.info("RECOMMENDATIONS")
        logger.info("=" * 60)
        
        if not self.test_results['aws_connectivity']:
            logger.info("❗ Configure AWS credentials: run 'aws configure' or set environment variables")
        
        if not self.test_results['knowledge_base_access']:
            logger.info("❗ Verify KNOWLEDGE_BASE_ID in .env file")
            logger.info("❗ Check if Knowledge Base exists in your AWS account")
        
        if not self.test_results['document_retrieval']:
            logger.info("❗ Upload documents to S3 and sync your Knowledge Base")
            logger.info("❗ Wait for ingestion to complete (can take 5-10 minutes)")
        
        if not self.test_results['end_to_end_query']:
            logger.info("❗ Check Knowledge Base model configuration")
            logger.info("❗ Verify IAM permissions for Bedrock model access")
        
        if self.test_results['error_details']:
            logger.info("\n📋 Error Details:")
            for i, error in enumerate(self.test_results['error_details'], 1):
                logger.info(f"   {i}. {error}")

def main():
    """Main function to run the test suite"""
    tester = AWSRAGTester()
    results = tester.run_all_tests()
    
    # Optionally save results to file
    results_file = 'aws_rag_test_results.json'
    try:
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"\n💾 Test results saved to: {results_file}")
    except Exception as e:
        logger.warning(f"Could not save results to file: {e}")
    
    # Exit with appropriate code
    if results['overall_status'] == 'PASS':
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()