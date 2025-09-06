# /scripts/upload_documents.py - Complete document upload implementation

import boto3
import os
import json
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentUploader:
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """Initialize the document uploader with S3 client"""
        self.bucket_name = bucket_name
        self.region = region
        
        try:
            self.s3_client = boto3.client('s3', region_name=region)
            logger.info(f"S3 client initialized for bucket: {bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Run 'aws configure' first.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def create_sample_documents(self) -> Dict[str, str]:
        """Create sample Singapore housing documents with realistic content"""
        
        documents = {
            # HDB Eligibility and Policies
            "hdb_eligibility_schemes.txt": """
            HDB FLAT ELIGIBILITY SCHEMES - SINGAPORE

            1. BUILD-TO-ORDER (BTO) SCHEME
            - Open to Singapore Citizens and Permanent Residents
            - Must form an eligible family nucleus
            - Monthly household income ceiling: $14,000 for non-mature estates, $21,000 for mature estates
            - First-timer families get priority allocation
            - Minimum Occupation Period (MOP): 5 years

            2. SALE OF BALANCE FLATS (SBF) SCHEME
            - For remaining flats after BTO exercises
            - Same eligibility criteria as BTO
            - Shorter waiting time but limited choices

            3. RE-OFFER OF BALANCE FLATS (ROF)
            - Flats returned by previous buyers
            - Available quarterly
            - Ready for occupation immediately

            FAMILY NUCLEUS REQUIREMENTS:
            - Married couples (including fiancé/fiancée)
            - Widowed/divorced persons with children
            - Single persons aged 35 and above (limited schemes)
            - Multi-generation families under Joint Singles Scheme

            PRIORITY SCHEMES:
            - First-Timer Priority Scheme
            - Second-Timer Priority Scheme  
            - Married Child Priority Scheme
            - Multi-Generation Priority Scheme
            """,

            "cpf_housing_grants.txt": """
            CPF HOUSING GRANTS FOR HDB FLATS

            1. ENHANCED CPF HOUSING GRANT (EHG)
            - Up to $80,000 for first-timer families
            - Income ceiling: $9,000 monthly household income
            - Additional $5,000 for families with young children
            - Can be used for BTO, SBF, or resale flats

            2. FAMILY GRANT
            - Up to $40,000 for first-timer married couples
            - Income ceiling: $14,000 monthly household income
            - For purchase of resale flats only
            - Must be within 4km of parents/married child

            3. PROXIMITY HOUSING GRANT (PHG)
            - Up to $30,000 for living near/with parents
            - Within same town or 4km radius
            - Available for both new and resale flats
            - Can be combined with other grants

            4. SINGLES GRANT
            - Up to $25,000 for eligible singles
            - Age 35 and above
            - Income ceiling: $7,000 monthly
            - For 2-room Flexi flats in non-mature estates

            GRANT CONDITIONS:
            - 10-year minimum occupation period
            - Cannot own other properties locally/overseas
            - Must occupy the flat as main residence
            - Subject to clawback if conditions not met
            """,

            "hdb_resale_procedures.txt": """
            HDB RESALE FLAT PROCEDURES

            RESALE PROCESS TIMELINE:
            1. Seller submits Intent to Sell (1-2 days)
            2. Buyer submits Intent to Buy (1-2 days)  
            3. Both parties endorse Application to Buy/Sell (1-2 weeks)
            4. HDB approval and valuation (2-3 weeks)
            5. Completion of sale (8-10 weeks from application)

            REQUIRED DOCUMENTS FOR BUYERS:
            - Identity cards of all buyers
            - Marriage certificate (if married)
            - Birth certificates of children
            - Income documents (payslips, tax assessments)
            - CPF statements
            - Bank statements
            - Option to Purchase from seller

            RESALE LEVY:
            - $15,000 for 4-room or smaller flats (second-timers)
            - $25,000 for 5-room or larger flats (second-timers)
            - Paid using CPF Ordinary Account
            - No levy for first-timer buyers

            CASH-OVER-VALUATION (COV):
            - Additional payment above HDB valuation
            - Paid in cash directly to seller
            - Not covered by CPF or housing loans
            - Negotiate based on market conditions

            LEGAL REQUIREMENTS:
            - All buyers must be on the title deed
            - Minimum occupation period applies
            - Cannot rent out entire flat during MOP
            - Must inform HDB of change in occupiers
            """,

            "bto_application_guide.txt": """
            BUILD-TO-ORDER (BTO) APPLICATION GUIDE

            APPLICATION PERIODS:
            - 4 BTO exercises per year (Feb, May, Aug, Nov)
            - Sales launch typically lasts 3 weeks
            - Online application through HDB InfoWEB only

            FLAT SELECTION PROCESS:
            1. Submit application during sales launch
            2. Computer balloting determines queue position
            3. Flat selection appointment scheduled by queue number
            4. Choose specific unit and floor level
            5. Sign Agreement for Lease

            PRIORITY ALLOCATION:
            First-Timer families: 95% of flats
            Second-Timer families: 5% of flats

            Additional priorities for:
            - Families with young children
            - Married couples living with parents
            - Multi-generation applications

            PAYMENT SCHEDULE:
            - Down payment: 10% of flat price
            - Progress payments during construction
            - Final payment upon key collection
            - Option fee: $500 (deducted from down payment)

            CONSTRUCTION TIMELINE:
            - Typical BTO construction: 3-4 years
            - Pre-construction activities: 6-12 months
            - Actual building works: 2.5-3 years
            - Defects liability period: 1 year

            IMPORTANT CONSIDERATIONS:
            - Cannot choose specific block/unit during application
            - Must be prepared for construction delays
            - Early key collection may incur additional costs
            - Renovation can only start after key collection
            """,

            "housing_loan_guidelines.txt": """
            HOUSING LOAN GUIDELINES FOR HDB FLATS

            HDB CONCESSIONARY LOAN:
            - Interest rate: 2.6% per annum (as of 2024)
            - Maximum loan tenure: 25 years
            - Maximum loan amount: 90% of flat price or valuation
            - Monthly installment cannot exceed 30% of gross monthly income

            BANK LOAN OPTIONS:
            - Competitive interest rates (floating/fixed)
            - Higher loan quantum possible
            - Shorter processing time
            - More flexible payment options
            - Subject to bank's credit assessment

            LOAN ELIGIBILITY REQUIREMENTS:
            - Minimum age: 21 years
            - Singapore Citizen or Permanent Resident
            - Sufficient income to service loan
            - Good credit history
            - Must not own other properties

            CPF USAGE FOR HOUSING:
            - Use CPF Ordinary Account for down payment
            - Monthly loan payments via CPF
            - Accrued interest charged on CPF usage
            - Must retain minimum sum in CPF account

            MORTGAGE INSURANCE:
            - Home Protection Scheme (HPS) for HDB loans
            - Mortgage Reducing Term Assurance (MRTA) for bank loans
            - Covers outstanding loan in event of death/disability
            - Premium can be paid using CPF

            REFINANCING OPTIONS:
            - Switch from HDB loan to bank loan
            - Switch between bank loans
            - Consider interest rate trends
            - Factor in legal and processing costs
            """
        }
        
        return documents
    
    def upload_file_to_s3(self, file_content: str, file_key: str) -> bool:
        """Upload a single file to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'source': 'singapore_housing_assistant',
                    'upload_date': str(Path(__file__).stat().st_mtime),
                    'document_type': 'policy_document'
                }
            )
            logger.info(f"✓ Uploaded: {file_key}")
            return True
            
        except ClientError as e:
            logger.error(f"✗ Failed to upload {file_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error uploading {file_key}: {e}")
            return False
    
    def upload_local_files(self, local_folder: str, s3_prefix: str = "housing-docs/") -> List[str]:
        """Upload files from local folder to S3"""
        uploaded_files = []
        
        if not os.path.exists(local_folder):
            logger.warning(f"Local folder does not exist: {local_folder}")
            return uploaded_files
        
        for file_path in Path(local_folder).rglob("*"):
            if file_path.is_file():
                # Read file content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Handle binary files (PDFs, etc.)
                    with open(file_path, 'rb') as f:
                        content = f.read()
                
                # Create S3 key
                relative_path = file_path.relative_to(local_folder)
                s3_key = f"{s3_prefix}{relative_path}"
                
                # Upload file
                if isinstance(content, str):
                    success = self.upload_file_to_s3(content, s3_key)
                else:
                    # Handle binary content
                    try:
                        self.s3_client.put_object(
                            Bucket=self.bucket_name,
                            Key=s3_key,
                            Body=content,
                            ContentType='application/octet-stream'
                        )
                        success = True
                        logger.info(f"✓ Uploaded binary file: {s3_key}")
                    except Exception as e:
                        logger.error(f"✗ Failed to upload binary file {s3_key}: {e}")
                        success = False
                
                if success:
                    uploaded_files.append(s3_key)
        
        return uploaded_files
    
    def upload_sample_documents(self, s3_prefix: str = "housing-docs/") -> List[str]:
        """Upload the sample documents to S3"""
        documents = self.create_sample_documents()
        uploaded_files = []
        
        logger.info(f"Uploading {len(documents)} sample documents to S3...")
        
        for filename, content in documents.items():
            s3_key = f"{s3_prefix}{filename}"
            
            if self.upload_file_to_s3(content, s3_key):
                uploaded_files.append(s3_key)
        
        logger.info(f"Upload complete. {len(uploaded_files)}/{len(documents)} files uploaded successfully.")
        return uploaded_files
    
    def list_bucket_contents(self, prefix: str = "housing-docs/") -> List[str]:
        """List contents of S3 bucket with given prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
                logger.info(f"Found {len(files)} files in bucket with prefix '{prefix}'")
                return files
            else:
                logger.info(f"No files found in bucket with prefix '{prefix}'")
                return []
                
        except ClientError as e:
            logger.error(f"Error listing bucket contents: {e}")
            return []
    
    def verify_upload(self, expected_files: List[str]) -> bool:
        """Verify that all expected files were uploaded"""
        bucket_files = self.list_bucket_contents()
        
        missing_files = []
        for expected_file in expected_files:
            if expected_file not in bucket_files:
                missing_files.append(expected_file)
        
        if missing_files:
            logger.error(f"Missing files: {missing_files}")
            return False
        else:
            logger.info("✓ All files uploaded successfully!")
            return True

def main():
    """Main function to run the document upload"""
    
    # Configuration - REPLACE WITH YOUR VALUES
    BUCKET_NAME = "everythgworks"  # Replace with your bucket name
    REGION = "us-east-1"  # Replace with your region
    
    try:
        # Initialize uploader
        uploader = DocumentUploader(BUCKET_NAME, REGION)
        
        # Upload sample documents
        logger.info("=== Starting Singapore Housing Documents Upload ===")
        uploaded_files = uploader.upload_sample_documents()
        
        # Verify upload
        logger.info("=== Verifying Upload ===")
        upload_success = uploader.verify_upload(uploaded_files)
        
        if upload_success:
            logger.info("=== Upload Complete! ===")
            logger.info("Next steps:")
            logger.info("1. Go to Bedrock Console → Knowledge bases")
            logger.info("2. Select your knowledge base")
            logger.info("3. Go to Data source → Sync")
            logger.info("4. Wait for sync to complete")
            logger.info("5. Test your knowledge base with queries")
        else:
            logger.error("=== Upload Failed! ===")
            logger.error("Please check the errors above and retry")
        
        # Optional: Upload any local documents
        local_docs_folder = "documents/singapore_housing"
        if os.path.exists(local_docs_folder):
            logger.info(f"=== Uploading local documents from {local_docs_folder} ===")
            local_uploaded = uploader.upload_local_files(local_docs_folder)
            logger.info(f"Uploaded {len(local_uploaded)} local files")
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise

if __name__ == "__main__":
    main()