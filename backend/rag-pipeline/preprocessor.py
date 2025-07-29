import re
import os
from typing import List, Dict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document

from dotenv import load_dotenv
load_dotenv()

class NigerianLawPreprocessor:
    
    def __init__(self):
        
        self.data_dir = "/app/data"
        self.faiss_index_path = os.path.join(self.data_dir, "faiss_index")
        os.makedirs(self.faiss_index_path, exist_ok=True)
        
        self.mongo_uri = os.getenv("MONGO_URI")
        self.mongo_db_name = os.getenv("MONGO_DB_NAME")
        self.mongo_collection_name = os.getenv("MONGO_COLLECTION_NAME")
        
        self.mongo_client = None
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
            length_function=len,
        )
        
        self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        print("Embedding model loaded.")
        
    def get_mongo_collection(self):
        if self.mongo_client is None:
            try:
                self.mongo_client = MongoClient(self.mongo_uri)
                self.mongo_client.admin.command('ping')
                db = self.mongo_client[self.mongo_db_name]
                collection = db[self.mongo_collection_name]
                print(f"Connected to MongoDB: {self.mongo_db_name}.{self.mongo_collection_name}")
                return collection
            except ConnectionFailure as e:
                print(f"MongoDB connection failed: {e}")
                return None
            return self.mongo_client[self.mongo_db_name][self.mongo_collection_name]
        
    def load_raw_data_from_mongo(self) -> List[Dict]:
        collection = self.get_mongo_collection()
        if collection is None:
            return []
        try:
            raw_documents = []
            for doc in collection.find({}):
                doc['_id'] = str(doc['_id'])
                raw_documents.append(doc)
            print(f"Loaded {len(raw_documents)} documents from MongoDB.")
            return raw_documents
        except Exception as e:
            print(f"Error loading documents: {e}")
            return []
        
    def clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>') \
            .replace('&quot;', '"').replace('&#x27;', "'").replace('&apos;', "'")

        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'\s+', ' ', text) 
            
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'[\!\?]{2,}', '!', text)
        text = re.sub(r'[\,\;\-]{2,}', ',', text)
        
        text = re.sub(r'[^a-zA-Z0-9\s.,!?;:"\'\-\(\)\[\]]', '', text)

        return text.strip()
    
    
    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        chunks = []
        
        for doc in documents:
            doc_id = doc.get("_id", doc.get("url", "unknown_doc_id"))
            doc_title = doc.get("metadata", doc.get("file_path"))
            raw_content = doc.get('content', '')
            
            if not raw_content:
                print(f"Skipping document {doc_id} due to empty content.")
                continue
            
            clean_content = self.clean_text(raw_content)
            
            text_chunks = self.text_splitter.split_text(clean_content)
            
            for i, chunk_content in enumerate(text_chunks):
                
                metadata = doc.get('metadata', {})
                metadata['source'] = doc.get('url', 'Unknown URL')
                metadata['doc_id'] = doc_id
                metadata['chunk_index'] = i
                metadata['title'] = doc.get("file_path")
                
                chunks.append({
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_{i}",
                    "source": doc.get('url', 'Unknown'), 
                    "title": doc_title,
                    "content": chunk_content,
                    "chunk_index": i,
                    "type": metadata.get("file_type"),
                    "metadata": metadata 
                })
                
            print(f"Chunked: {doc_title} ({len(text_chunks)} chunks)")
        print(f"Total chunks created: {len(chunks)}")
        return chunks
    
    def filter_quality_chunks(self, chunks: List[Dict]) -> List[Dict]:
        filtered = []
        
        initial_count = len(chunks)
        
        for chunk in chunks:
            content = chunk.get('content', '')
            if not content:
                continue
            
            if len(content) < 100:
                continue
            
            alphanum_chars = len(re.findall(r'[a-zA-Z0-9]', content))
            if len(content) > 0 and (alphanum_chars / len(content)) < 0.5:
                continue
        
            number_chars = len(re.findall(r'\d', content))
            if len(content) > 0 and (number_chars / len(content)) > 0.4: 
                continue
            
            filtered.append(chunk)
            
        print(f"Quality chunks: {len(filtered)} / {initial_count}")
        return filtered
    
    def save_chunks_to_faiss(self, chunks: List[Dict]):
        
        if not chunks:
            print("No chunks to save.")
            return
        
        langchain_docs = []
        
        for chunk in chunks:
            langchain_docs.append(
                Document(
                    page_content=chunk['content'],
                    metadata=chunk['metadata']
                )
            )
            
        faiss_store = FAISS.from_documents(langchain_docs, self.embedding_model)
        faiss_store.save_local(self.faiss_index_path)
        print(f"FAISS index saved at: {self.faiss_index_path}")
        
    def process_all_data(self):
        print("🚀 Starting data preprocessing pipeline...")
        raw_documents = self.load_raw_data_from_mongo()
        chunks = self.chunk_documents(raw_documents)
        filtered_chunks = self.filter_quality_chunks(chunks)
        self.save_chunks_to_faiss(filtered_chunks)
        print("All data processed and saved!")


if __name__ == "__main__":
    processor = NigerianLawPreprocessor()
    processor.process_all_data()

    if os.path.exists(processor.faiss_index_path):
        print(f"\nFAISS index directory exists: {processor.faiss_index_path}")
    else:
        print("\nFAISS index not found.")