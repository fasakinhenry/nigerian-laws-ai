import os
from typing import List, Dict, Optional
from datetime import datetime

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document

from dotenv import load_dotenv
load_dotenv()

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
            template="""You are a search query optimizer for vector database searches. Your task is to reformulate user queries into more effective search terms.
            Given a user's search query, you must:
            1. Identify the core concepts and intent
            2. Add relevant synonyms and related terms
            3. Remove irrelevant filler words
            4. Structure the query to emphasize key terms
            5. Include technical or domain-specific terminology if applicable

            Provide only the optimized search query without any explanations, greetings, or additional commentary.

            Example input: "how to start a company in Nigeria"
            Example output: "corporate affairs commission company registration requirements business incorporation enterprise formation legal documents"

            Constraints:
            - Output only the enhanced search terms
            - Keep focus on searchable concepts
            - Include both specific and general related terms
            - Maintain all important meaning from original query

            Original Query: {original_query}

            Optimized Query:""",
            input_variables=["original_query"]
        )
        
        self.prompt_template = PromptTemplate(
            template="""You are an expert on Nigerian laws. Use the following context to answer the question accurately and informatively.
            If the context doesn't contain enough information, state clearly that you cannot answer based on the provided information.
            Always provide specific dates, names, and events when available.
            Keep your answer informative but concise. If context dose'nt match the question simply respond with I am a Nigerian law assistant. Please provide a meaningful question. For example: 'What are the legal requirements for registering a business in Nigeria?'.

            Context:
            {context}

            Question: {question}

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
        print(f"Rewritten query: '{rewritten_query.strip()}'")
        return rewritten_query.strip()
        
    def search_relevant_chunks(self, query: str, top_k: int) -> List[Document]:
        
        rewritten_query = self._rewrite_query(query)
        
        print(f"Searching for top {top_k} relevant chunks for query: '{query[:50]}'")
        
        relevant_documents = self.vector_store.similarity_search(rewritten_query, k=top_k)
        
        print(f"Found {len(relevant_documents)} relevant documents.")
        return relevant_documents
    
    def generate_answer(self, question: str) -> Dict:
        
        relevant_documents = self.search_relevant_chunks(question, top_k=3)
        
        if not relevant_documents:
            print("No relevant documents found. Returning custom response.")
            return {
                "question": question,
                "answer": "I am a Nigerian law assistant. Please provide a meaningful question. For example: 'What are the legal requirements for registering a business in Nigeria?'",
                "sources": [],
                "relevant_chunks_found": 0,
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
        
        print(f"\nGenerated context for question '{question[:50]}...':\n{context}")
        
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
    
    