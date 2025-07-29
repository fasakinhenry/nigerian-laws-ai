import os
import time
from typing import List, Dict, Optional
import logging
from datetime import datetime
from dotenv import load_dotenv

from langchain_community.document_loaders.git import GitLoader
from langchain_core.documents import Document

from .mongo_setup import NigerianLawsDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME") 
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

TARGET_GITHUB_REPO_URL: str = "https://github.com/mykeels/nigerian-laws"

def _extract_owner_repo_from_url(url: str) -> Optional[tuple[str, str]]:
    
    try:
        url_parts = url.split('?')[0].split('#')[0]
        path_segments = [segment for segment in url_parts.split('/') if segment]
        
        if "github.com" in path_segments:
            github_index = path_segments.index("github.com")
            if len(path_segments) > github_index + 2:
                owner = path_segments[github_index + 1]
                repo = path_segments[github_index + 2]
                
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return owner, repo
            
        logger.warning(f"Could not extract owner and repo from GitHub URL: {url}")
        return None
    except Exception as e:
        logger.error(f"Error parsing GitHub URL {url}: {e}")
        return None
    
parsed_repo = _extract_owner_repo_from_url(TARGET_GITHUB_REPO_URL)
NIGERIAN_LAWS_GITHUB_REPOS_FOR_LOADER: List[tuple[str, str]] = []
if parsed_repo:
    NIGERIAN_LAWS_GITHUB_REPOS_FOR_LOADER.append(parsed_repo)
else:
    logger.critical("Failed to parse the target GitHub URL")
    
class DataCollector:
    
    def __init__(self):
        
        self.db_manager = NigerianLawsDatabase(MONGO_URI, MONGO_DB_NAME)
        self.collection = self.db_manager.get_collection(MONGO_COLLECTION_NAME)
        
        logger.info("DataCollector initialized successfully.")
    
    def save_document(self, data: Dict) -> bool:
        
        unique_identifier = data.get('url')
        
        try:
            result = self.collection.update_one(
                {'url': unique_identifier},
                {'$set': data},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"Inserted new document: {unique_identifier} (ID: {result.upserted_id})")
            elif result.modified_count > 0:
                logger.info(f"Updated existing document: {unique_identifier}")
            else:
                logger.debug(f"Document: {unique_identifier} already exists and no changes detected.")
            return True
        
        except Exception as e:
            logger.error(f"Error saving document to MongoDB for {unique_identifier}: {e}")
            return False
        
    def collect_github_repo_data(self, repo_url: str, branch: str = "master"):
        
        if not repo_url:
            logger.info("No GitHub repository URL provided")
            return
        
        try:
            clean_url = repo_url.split('?')[0]
            path_parts = clean_url.strip('/').split('/')
            owner = path_parts[-2]
            repo_name = path_parts[-1]
            
            if not owner or not repo_name:
                raise ValueError("Could not parse owner and repo_name from provided URL.")
            
            repo_full_url = f"https://github.com/{owner}/{repo_name}"
            
        except Exception as e:
            logger.error(f"Invalid GitHub repository URL format: {repo_url}. Error: {e}")
            return
        
        logger.info(f"Scraping GitHub repository: {repo_full_url}")
        
        try:
            temp_repo_path = f"/tmp/{owner}_{repo_name}"
            
            loader = GitLoader(
                repo_path=temp_repo_path,
                clone_url=repo_full_url,
                branch=branch,
                file_filter=lambda file_path: file_path.endswith((".md", ".txt", ".pdf", ".docx", ".html"))
            )
            
            langchain_docs: List[Document] = loader.load()
            
            repo_processed_count = 0
            
            if not langchain_docs:
                logger.info(f"No documents found or loaded from {repo_full_url}")
                return

            for doc in langchain_docs:
                document_data = {
                    "url": doc.metadata.get("source", f"{repo_full_url}/{doc.metadata.get('file_path', 'unknown')}"), 
                    "content": doc.page_content,
                    "scraped_at": datetime.utcnow(),
                    "source_type": "github_repo",
                    "metadata": {
                        "repo_url": repo_full_url,
                        "file_path": doc.metadata.get("file_path"),
                        "file_type": doc.metadata.get("file_type"),
                        "branch": branch,
                        "title": doc.metadata.get("title", os.path.basename(doc.metadata.get("file_path", "unknown_file"))),
                    }
                }
                
                if self.save_document(document_data):
                    repo_processed_count += 1
            
            logger.info(f"Finished scraping {repo_full_url}. Documents processed/updated: {repo_processed_count}.")
            
            # Clean up temporary directory
            import shutil
            if os.path.exists(temp_repo_path):
                shutil.rmtree(temp_repo_path)

        except Exception as e:
            logger.error(f"An error occurred during GitHub repo scraping for {repo_full_url}: {e}")
        
        time.sleep(2) 

    def __del__(self):
        if self.db_manager:
            self.db_manager.close()