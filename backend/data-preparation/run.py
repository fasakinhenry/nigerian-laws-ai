import logging

from .data_collector import DataCollector, TARGET_GITHUB_REPO_URL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_data_collection_pipeline():
    
    logger.info("Starting Nigerian Laws Data Collection Pipeline")
    
    try:
        
        data_collector = DataCollector()
        
        if TARGET_GITHUB_REPO_URL:
            logger.info(f"Starting GitHub repository scraping from: {TARGET_GITHUB_REPO_URL}")
            data_collector.collect_github_repo_data(TARGET_GITHUB_REPO_URL, branch="master")
        else:
            logger.info("No target GitHub repository URL defined.")
            
        logger.info("Nigerian Laws Data Collection Pipeline completed successfully.")
        
    except Exception as e:
        logger.critical(f"An unhandled error occurred during data collection pipeline execution: {e}")
        exit(1) 

if __name__ == "__main__":
    run_data_collection_pipeline()