import os
from typing import List, Dict, Optional
from datetime import datetime
import logging

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NigerianLawRAG:
    
    def __init__(self, model_type: str = "ollama", model_name: Optional[str] = None):
        
        self.faiss_index_path = os.path.join("/app", "data", "faiss_index") 
        self.model_type = model_type
        self.model_name = os.getenv("OLLAMA_MODEL_NAME")
        self.max_context_length = 3500
        
        self.embedding_model = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
        print("Embedding model loaded.")
        
        self.llm = self.initialize_llm()
        
        self.vector_store = self.load_vector_store()
        
        self.query_rewrite_prompt = PromptTemplate(
            template="""You are a legal search query optimizer. Reformulate the user's query to find relevant Nigerian legal documents.

            For the query, identify:
            1. Legal domain (criminal law, corporate law, constitutional law, etc.)
            2. Key legal concepts and terminology
            3. Relevant Nigerian acts or laws
            4. Synonyms and related legal terms

            Original Query: {original_query}

            Enhanced Legal Search Query:""",
            input_variables=["original_query"]
        )
        
        self.unrelated_query_prompt = PromptTemplate(
            template="""You are an expert on Nigerian law. The user has asked the question {question}
            which is unrelated to your expertise, nudge them towards asking questions related to your expertise
            in Nigeria law.
            """,
            input_variables=["question"]
        )
        
        self.prompt_template = PromptTemplate(
            template="""you are an expert on Nigerian law answer this user's 
                {question}

                based on the following context {context}

                - You must answer the question directly and nothing more.

                Answer:""",
                input_variables=["context", "question"]
        )

    def initialize_llm(self):
        return OllamaLLM(
            model=self.model_name, 
            temperature=0.6, 
            top_p=0.8, 
            repeat_penalty=1.05, 
            top_k=20,
            base_url=os.getenv("OLLAMA_BASE_URL")
        )
    
    def load_vector_store(self):
        print(f"Loading FAISS index from: {self.faiss_index_path}")
        
        try:
            faiss_vector_store = FAISS.load_local(
                folder_path=self.faiss_index_path,
                embeddings=self.embedding_model,
                allow_dangerous_deserialization=True
            )
            print("FAISS index loaded successfully.")
            return faiss_vector_store
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            raise
    
    def _rewrite_query(self, query: str) -> str:
        rewrite_prompt_formatted = self.query_rewrite_prompt.format(original_query=query)
        rewritten_query = self.llm.invoke(rewrite_prompt_formatted)
        logger.debug(f"Rewritten query: '{rewritten_query.strip()}'") 
        return rewritten_query.strip()
        
    def search_relevant_chunks(self, query: str, top_k: int) -> List[Document]:
        
        rewritten_query = self._rewrite_query(query)
        
        print(f"Searching for top {top_k} relevant chunks for query: '{query[:50]}'")
        
        relevant_documents = self.vector_store.similarity_search(rewritten_query, k=top_k)
        
        logger.info(f"Found {len(relevant_documents)} relevant documents.")
        return relevant_documents
    
    def _is_context_relevant(self, question: str, documents: List[Document]) -> bool:

        question_keywords = set(question.lower().split())
        
        for doc in documents:
            doc_content = doc.page_content.lower()
            doc_title = doc.metadata.get("file_path", "").lower()
            
            content_words = set(doc_content.split())
            title_words = set(doc_title.split())
            
            overlap = question_keywords.intersection(content_words.union(title_words))
            
            if len(overlap) >= 5: 
                return True
        
        return False
    
    def generate_answer(self, question: str) -> Dict:
        relevant_documents = self.search_relevant_chunks(question, top_k=7)
        
        if not relevant_documents or not self._is_context_relevant(question, relevant_documents):
            
            prompt_formatted = self.unrelated_query_prompt.format(question=question)
            
            generated_answer = self.llm.invoke(prompt_formatted)
            
            return {
                "question": question,
                "answer": generated_answer.strip(),
                "sources": [],
                "relevant_chunks_found": len(relevant_documents),
                "context_chunks_used": 0,
                "timestamp": datetime.now().isoformat()
            }
    
        
        context_parts = []
        context_length = 0
        sources = set()
        
        for doc in relevant_documents:
            doc_title = doc.metadata.get("file_path")
            doc_url = doc.metadata.get('url', 'No URL') 
            chunk_content = doc.page_content
            
            source_citation = f"Source: {doc_title} ({doc_url})" if doc_url and doc_url != 'Unknown URL' else f"Source: {doc_title}"
            
            chunk_text = f"{source_citation}\nContent: {chunk_content}\n\n"
            
            if context_length + len(chunk_text) > self.max_content_length:
                break
            
            context_parts.append(chunk_text)
            context_length += len(chunk_text)
            
            sources.add(f"{doc_title} ({doc_url})")
            
        context = "".join(context_parts)
        
        logger.debug(f"Generated context for question '{question[:50]}...':\n{context}")
        
        print(f"Generating answer using {self.model_type} ({self.model_name})...")
        prompt = self.prompt_template.format(context=context, question=question)
        
        answer = self.llm.invoke(prompt)
        
        response = {
            "question": question,
            "answer": answer,
            "sources": list(sources),
            "relevant_chunks_found": len(relevant_documents),
            "context_chunks_used": len(context_parts),
            "timestamp": datetime.now().isoformat()
        }
        
        return response
    
    def ask_question(self, question: str) -> Dict:
        
        response = self.generate_answer(question)
        
        return response
    
    