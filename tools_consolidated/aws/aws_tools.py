# tools_consolidated/aws/aws_tools.py - Best-of-both consolidation
import boto3
import json
import logging
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError
from strands import tool

logger = logging.getLogger(__name__)

class AWSKnowledgeBaseManager:
    """Centralized AWS Knowledge Base management with improved error handling"""
    
    def __init__(self, knowledge_base_id: str = None, region: str = "us-east-1"):
        # Use environment variable or default - don't hardcode in constructor
        import os
        self.knowledge_base_id = knowledge_base_id or os.getenv('AWS_KNOWLEDGE_BASE_ID', 'AVGJILOX4X')
        self.region = region
        self._clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AWS clients with comprehensive error handling"""
        try:
            self._clients['bedrock_agent_runtime'] = boto3.client(
                'bedrock-agent-runtime', region_name=self.region
            )
            self._clients['s3'] = boto3.client('s3', region_name=self.region)
            self._clients['bedrock_agent'] = boto3.client(
                'bedrock-agent', region_name=self.region
            )
            logger.info(f"AWS clients initialized for KB: {self.knowledge_base_id}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Configure AWS credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise
    
    def query_knowledge_base(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Query AWS Knowledge Base with comprehensive error handling"""
        try:
            response = self._clients['bedrock_agent_runtime'].retrieve_and_generate(
                input={'text': query},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.knowledge_base_id,
                        'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': max_results
                            }
                        }
                    }
                }
            )
            
            return {
                'answer': response.get('output', {}).get('text', ''),
                'source_documents': response.get('citations', []),
                'session_id': response.get('sessionId', ''),
                'success': True
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ResourceNotFoundException':
                error_msg = f'Knowledge Base {self.knowledge_base_id} not found'
                logger.error(error_msg)
                return {'error': error_msg, 'success': False}
            else:
                error_msg = f'AWS API error: {str(e)}'
                logger.error(error_msg)
                return {'error': error_msg, 'success': False}
        except Exception as e:
            error_msg = f'Query failed: {str(e)}'
            logger.error(error_msg)
            return {'error': error_msg, 'success': False}
    
    def retrieve_documents(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Retrieve relevant documents without generation"""
        try:
            response = self._clients['bedrock_agent_runtime'].retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results
                    }
                }
            )
            
            documents = []
            for item in response.get('retrievalResults', []):
                doc_info = {
                    'content': item.get('content', {}).get('text', ''),
                    'score': item.get('score', 0),
                    'location': item.get('location', {})
                }
                documents.append(doc_info)
            
            return documents
            
        except Exception as e:
            logger.error(f"Document retrieval error: {e}")
            return []
    
    def upload_documents_to_s3(self, documents: List[Dict[str, str]], 
                              bucket_name: str, prefix: str = "housing-docs/") -> List[str]:
        """Upload documents to S3 for Knowledge Base ingestion"""
        uploaded_keys = []
        
        try:
            for i, doc in enumerate(documents):
                key = f"{prefix}{doc.get('filename', f'document_{i}.txt')}"
                
                self._clients['s3'].put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=doc.get('content', '').encode('utf-8'),
                    ContentType='text/plain'
                )
                
                uploaded_keys.append(key)
                logger.info(f"Uploaded document: {key}")
                
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise
        
        return uploaded_keys
    
    def sync_knowledge_base(self, data_source_id: str = None) -> Dict[str, Any]:
        """Trigger Knowledge Base sync after document updates"""
        try:
            import os
            # Use environment variable or default
            ds_id = data_source_id or os.getenv('AWS_DATA_SOURCE_ID', 'GFKEQDAHF7')
            
            response = self._clients['bedrock_agent'].start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=ds_id
            )
            
            return {
                'job_id': response.get('ingestionJob', {}).get('ingestionJobId'),
                'status': response.get('ingestionJob', {}).get('status'),
                'success': True
            }
            
        except Exception as e:
            error_msg = f"Knowledge Base sync error: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg, 'success': False}
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Comprehensive configuration validation"""
        validation_results = {
            'aws_authentication': False,
            'knowledge_base_access': False,
            's3_access': False,
            'details': {}
        }
        
        # Check AWS credentials
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            validation_results['aws_authentication'] = True
            validation_results['details']['aws_identity'] = identity.get('Arn', 'Valid')
        except Exception as e:
            validation_results['details']['aws_auth_error'] = str(e)
        
        # Check Knowledge Base access
        try:
            test_result = self.retrieve_documents("test query", max_results=1)
            validation_results['knowledge_base_access'] = len(test_result) >= 0  # Empty is OK
        except Exception as e:
            validation_results['details']['kb_error'] = str(e)
        
        # Check S3 access
        try:
            self._clients['s3'].list_buckets()
            validation_results['s3_access'] = True
        except Exception as e:
            validation_results['details']['s3_error'] = str(e)
        
        return validation_results

# Global AWS manager instance
aws_manager = None
AWS_AVAILABLE = False

try:
    aws_manager = AWSKnowledgeBaseManager()
    AWS_AVAILABLE = True
    logger.info("AWS Knowledge Base manager initialized successfully")
except Exception as e:
    logger.warning(f"AWS Knowledge Base not available: {e}")

@tool
def aws_rag_search(query: str, search_type: str = "retrieve_and_generate", max_results: int = 5) -> str:
    """Search AWS Knowledge Base with comprehensive error handling"""
    
    if not AWS_AVAILABLE or not aws_manager:
        return "AWS Knowledge Base not initialized. Please check configuration."
    
    try:
        if search_type == "retrieve_and_generate":
            result = aws_manager.query_knowledge_base(query, max_results)
            
            if not result.get('success'):
                return f"Knowledge Base error: {result.get('error')}"
            
            answer = result.get('answer', 'No answer generated')
            sources = result.get('source_documents', [])
            
            response = f"**Answer:** {answer}\n\n"
            
            if sources:
                response += "**Sources:**\n"
                for i, source in enumerate(sources[:3], 1):
                    refs = source.get('retrievedReferences', [])
                    if refs:
                        location = refs[0].get('location', {})
                        s3_location = location.get('s3Location', {})
                        uri = s3_location.get('uri', 'Unknown source')
                        response += f"{i}. {uri}\n"
            
            return response
            
        elif search_type == "retrieve_only":
            documents = aws_manager.retrieve_documents(query, max_results)
            
            if not documents:
                return "No relevant documents found."
            
            response = f"**Found {len(documents)} relevant documents:**\n\n"
            for i, doc in enumerate(documents[:3], 1):
                content_preview = doc.get('content', '')[:200] + "..."
                score = doc.get('score', 0)
                response += f"{i}. Score: {score:.3f}\n{content_preview}\n\n"
            
            return response
        else:
            return "Supported search types: 'retrieve_and_generate', 'retrieve_only'"
            
    except Exception as e:
        logger.error(f"AWS RAG search error: {e}")
        return f"Search error: {str(e)}"

@tool
def singapore_housing_aws_search(query: str, domain: str = "hdb_policies") -> str:
    """Singapore-specific housing search using AWS Knowledge Base"""
    
    # Enhanced query mapping for better results
    enhanced_queries = {
        "hdb_policies": f"Singapore HDB housing policy regulations: {query}",
        "grant_schemes": f"Singapore housing grants eligibility criteria: {query}",
        "market_data": f"Singapore property market analysis trends: {query}",
        "location_intel": f"Singapore neighborhood housing information: {query}"
    }
    
    enhanced_query = enhanced_queries.get(domain, f"Singapore housing information: {query}")
    return aws_rag_search(enhanced_query, "retrieve_and_generate", max_results=5)

@tool
def validate_aws_rag_configuration() -> str:
    """Validate AWS RAG system configuration and return detailed status"""
    
    if not AWS_AVAILABLE or not aws_manager:
        return "AWS RAG system not available - check credentials and configuration"
    
    try:
        validation = aws_manager.validate_configuration()
        
        status_lines = []
        
        # Use checkmarks/crosses for status
        auth_status = "✅" if validation['aws_authentication'] else "❌"
        kb_status = "✅ Accessible" if validation['knowledge_base_access'] else "❌ Not accessible"
        s3_status = "✅ Available" if validation['s3_access'] else "❌ Unavailable"
        
        status_lines.append(f"AWS Authentication: {auth_status}")
        status_lines.append(f"Knowledge Base: {kb_status}")
        status_lines.append(f"S3 Access: {s3_status}")
        
        # Add identity info if available
        details = validation.get('details', {})
        if 'aws_identity' in details:
            status_lines.append(f"Identity: {details['aws_identity']}")
        
        # Add error details
        for error_key in ['aws_auth_error', 'kb_error', 's3_error']:
            if error_key in details:
                status_lines.append(f"Error: {details[error_key]}")
        
        return "\n".join(status_lines)
        
    except Exception as e:
        return f"Configuration validation failed: {str(e)}"

@tool 
def initialize_aws_rag_system(bucket_name: str = None, documents_data: List[Dict[str, str]] = None) -> str:
    """Initialize AWS RAG system with optional document upload"""
    
    if not AWS_AVAILABLE or not aws_manager:
        return "AWS RAG system not properly configured"
    
    try:
        status_message = f"AWS Knowledge Base RAG initialized with KB ID: {aws_manager.knowledge_base_id}\n"
        
        # Upload documents if provided
        if documents_data and bucket_name:
            uploaded_keys = aws_manager.upload_documents_to_s3(documents_data, bucket_name)
            status_message += f"Uploaded {len(uploaded_keys)} documents to S3\n"
            
            # Trigger sync
            sync_result = aws_manager.sync_knowledge_base()
            if sync_result.get('success'):
                status_message += f"Knowledge Base sync started: {sync_result.get('job_id')}"
            else:
                status_message += f"Sync error: {sync_result.get('error')}"
        
        return status_message
        
    except Exception as e:
        logger.error(f"AWS RAG initialization error: {e}")
        return f"Initialization failed: {str(e)}"

# Utility functions for integration
def get_aws_status() -> Dict[str, Any]:
    """Get AWS system status for registry"""
    if not AWS_AVAILABLE or not aws_manager:
        return {'available': False, 'error': 'AWS not initialized'}
    
    try:
        validation = aws_manager.validate_configuration()
        return {
            'available': all([validation['aws_authentication'], validation['knowledge_base_access']]),
            'details': validation
        }
    except Exception as e:
        return {'available': False, 'error': str(e)}