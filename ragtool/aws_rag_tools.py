# aws_rag_tools.py - Proper AWS Knowledge Base Integration

import boto3
import json
import logging
from typing import List, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from strands import tool

logger = logging.getLogger(__name__)

class AWSKnowledgeBaseRAG:
    def __init__(self, knowledge_base_id: str, region: str = "us-east-1"):
        """Initialize AWS Knowledge Base RAG with proper error handling"""
        self.knowledge_base_id = "AVGJILOX4X"
        self.region = region
        
        try:
            # Initialize AWS clients
            self.bedrock_agent_runtime = boto3.client(
                'bedrock-agent-runtime',
                region_name=region
            )
            self.s3_client = boto3.client('s3', region_name=region)
            self.bedrock_agent = boto3.client('bedrock-agent', region_name=region)
            
            logger.info(f"AWS Knowledge Base RAG initialized for KB: {knowledge_base_id}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Configure AWS credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise

    def query_knowledge_base(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Query AWS Knowledge Base with proper error handling"""
        try:
            response = self.bedrock_agent_runtime.retrieve_and_generate(
                input={
                    'text': query
                },
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
                'session_id': response.get('sessionId', '')
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ResourceNotFoundException':
                logger.error(f"Knowledge Base {self.knowledge_base_id} not found")
                return {'error': 'Knowledge Base not found'}
            else:
                logger.error(f"AWS API error: {e}")
                return {'error': f'AWS API error: {str(e)}'}
        except Exception as e:
            logger.error(f"Knowledge Base query error: {e}")
            return {'error': f'Query failed: {str(e)}'}

    def retrieve_documents(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Retrieve relevant documents without generation"""
        try:
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
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
                
                self.s3_client.put_object(
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

    def sync_knowledge_base(self) -> Dict[str, Any]:
        """Trigger Knowledge Base sync after document updates"""
        try:
            response = self.bedrock_agent.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId='GFKEQDAHF7'  # Replace with actual data source ID
            )
            
            return {
                'job_id': response.get('ingestionJob', {}).get('ingestionJobId'),
                'status': response.get('ingestionJob', {}).get('status')
            }
            
        except Exception as e:
            logger.error(f"Knowledge Base sync error: {e}")
            return {'error': str(e)}

# Initialize the AWS RAG system
# Replace with your actual Knowledge Base ID
KNOWLEDGE_BASE_ID = "YOUR_KNOWLEDGE_BASE_ID"
aws_rag = None

try:
    aws_rag = AWSKnowledgeBaseRAG(KNOWLEDGE_BASE_ID)
except Exception as e:
    logger.error(f"Failed to initialize AWS RAG: {e}")

@tool
def aws_rag_search(query: str, search_type: str = "retrieve_and_generate", max_results: int = 5) -> str:
    """Search AWS Knowledge Base with proper error handling"""
    
    if not aws_rag:
        return "AWS Knowledge Base not initialized. Please check configuration."
    
    try:
        if search_type == "retrieve_and_generate":
            result = aws_rag.query_knowledge_base(query, max_results)
            
            if 'error' in result:
                return f"Knowledge Base error: {result['error']}"
            
            answer = result.get('answer', 'No answer generated')
            sources = result.get('source_documents', [])
            
            response = f"**Answer:** {answer}\n\n"
            
            if sources:
                response += "**Sources:**\n"
                for i, source in enumerate(sources[:3], 1):  # Show top 3 sources
                    location = source.get('retrievedReferences', [{}])[0].get('location', {})
                    s3_location = location.get('s3Location', {})
                    uri = s3_location.get('uri', 'Unknown source')
                    response += f"{i}. {uri}\n"
            
            return response
            
        elif search_type == "retrieve_only":
            documents = aws_rag.retrieve_documents(query, max_results)
            
            if not documents:
                return "No relevant documents found."
            
            response = f"**Found {len(documents)} relevant documents:**\n\n"
            for i, doc in enumerate(documents[:3], 1):  # Show top 3
                content_preview = doc.get('content', '')[:200] + "..."
                score = doc.get('score', 0)
                response += f"{i}. Score: {score:.3f}\n{content_preview}\n\n"
            
            return response
            
    except Exception as e:
        logger.error(f"AWS RAG search error: {e}")
        return f"Search error: {str(e)}"

@tool
def initialize_aws_rag_system(bucket_name: str, documents_data: List[Dict[str, str]] = None) -> str:
    """Initialize AWS RAG system with document upload"""
    
    if not aws_rag:
        return "AWS RAG system not properly configured"
    
    try:
        status_message = f"AWS Knowledge Base RAG initialized with KB ID: {KNOWLEDGE_BASE_ID}\n"
        
        # Upload documents if provided
        if documents_data and bucket_name:
            uploaded_keys = aws_rag.upload_documents_to_s3(documents_data, bucket_name)
            status_message += f"Uploaded {len(uploaded_keys)} documents to S3\n"
            
            # Trigger sync
            sync_result = aws_rag.sync_knowledge_base()
            if 'error' not in sync_result:
                status_message += f"Knowledge Base sync started: {sync_result.get('job_id')}"
            else:
                status_message += f"Sync error: {sync_result['error']}"
        
        return status_message
        
    except Exception as e:
        logger.error(f"AWS RAG initialization error: {e}")
        return f"Initialization failed: {str(e)}"

@tool  
def singapore_housing_aws_search(query: str, domain: str = "hdb_policies") -> str:
    """Singapore-specific housing search using AWS Knowledge Base"""
    
    # Enhance query with Singapore context
    enhanced_queries = {
        "hdb_policies": f"Singapore HDB policy: {query}",
        "grant_schemes": f"Singapore housing grants eligibility: {query}",
        "market_data": f"Singapore property market trends: {query}",
        "location_intel": f"Singapore neighbourhood analysis: {query}"
    }
    
    enhanced_query = enhanced_queries.get(domain, f"Singapore housing: {query}")
    
    return aws_rag_search(enhanced_query, "retrieve_and_generate", max_results=5)

# Configuration validation
@tool
def validate_aws_rag_configuration() -> str:
    """Validate AWS RAG system configuration"""
    
    validation_results = []
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        validation_results.append(f"✅ AWS Authentication: {identity.get('Arn', 'Valid')}")
    except Exception as e:
        validation_results.append(f"❌ AWS Authentication: {str(e)}")
    
    # Check Knowledge Base access
    if aws_rag:
        try:
            # Test query
            test_result = aws_rag.retrieve_documents("test query", max_results=1)
            validation_results.append("✅ Knowledge Base: Accessible")
        except Exception as e:
            validation_results.append(f"❌ Knowledge Base: {str(e)}")
    else:
        validation_results.append("❌ Knowledge Base: Not initialized")
    
    # Check S3 access
    try:
        s3 = boto3.client('s3')
        s3.list_buckets()
        validation_results.append("✅ S3 Access: Available")
    except Exception as e:
        validation_results.append(f"❌ S3 Access: {str(e)}")
    
    return "\n".join(validation_results)