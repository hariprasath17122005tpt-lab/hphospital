#!/usr/bin/env python3
"""
PURE DATASET MEDICAL CHATBOT - v3
- Only uses 256k+ medical Q&A dataset
- No hardcoded responses
- No generative models
- Direct database matching
- Always returns real doctor answers from dataset
"""
import json
import os
from pathlib import Path
from typing import List, Dict
from difflib import SequenceMatcher
import threading
import time
import warnings
import re

warnings.filterwarnings('ignore')

class MedicalDatasetChatbot:
    """
    Pure dataset-based medical chatbot
    - Searches 256,878 real medical Q&A pairs
    - Returns only real doctor responses
    - No hardcoded fallbacks during search
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MedicalDatasetChatbot, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.dataset_dir = Path("trained_models/medical_dataset")
        self.qa_pairs = []
        self.qa_indexed = {}
        self.ready = False
        self._initialized = True
        
        # Load dataset
        self._load_dataset()
    
    def _load_dataset(self):
        """Load the medical Q&A dataset"""
        try:
            qa_file = self.dataset_dir / "medical_qa_pairs.json"
            
            if qa_file.exists():
                print("⏳ Loading medical Q&A dataset... (256k+ Q&A pairs)")
                with open(qa_file, 'r', encoding='utf-8') as f:
                    self.qa_pairs = json.load(f)
                print(f"✅ Loaded {len(self.qa_pairs)} Q&A pairs from dataset")
                
                self._create_index()
            else:
                print(f"❌ Dataset file not found: {qa_file}")
                return
            
            self.ready = len(self.qa_pairs) > 0
            
            if self.ready:
                print("✅ Dataset Chatbot Ready!")
        
        except Exception as e:
            print(f"❌ Error loading dataset: {e}")
            self.ready = False
    
    def _create_index(self):
        """Create keyword index for fast searching"""
        try:
            print("📝 Building keyword index...")
            
            # Minimal stopwords - keep medical terms
            stopwords = {'what', 'is', 'how', 'are', 'the', 'and', 'or', 'for', 'you', 'your', 'i', 'a', 'an', 'my', 'from', 'with'}
            
            for idx, qa in enumerate(self.qa_pairs):
                if idx % 50000 == 0:
                    print(f"   Indexed {idx:,} pairs...")
                
                question = qa['question'].lower()
                words = re.findall(r'\w+', question)
                
                # Index all significant words (keep more terms for medical)
                for word in words:
                    if len(word) >= 3 and word not in stopwords:
                        if word not in self.qa_indexed:
                            self.qa_indexed[word] = []
                        if not self.qa_indexed[word] or self.qa_indexed[word][-1] != idx:
                            self.qa_indexed[word].append(idx)
            
            print(f"✅ Created index with {len(self.qa_indexed):,} keywords")
        except Exception as e:
            print(f"❌ Index creation failed: {e}")
    
    def _find_best_matches(self, query: str, top_k: int = 10) -> List[Dict]:
        """Find best matching Q&A pairs from dataset"""
        query_lower = query.lower()
        query_words = [w for w in re.findall(r'\w+', query_lower) if len(w) >= 3]
        
        if not query_words:
            return []
        
        # Find candidates using keyword index
        candidate_counts = {}
        for word in query_words:
            if word in self.qa_indexed:
                for idx in self.qa_indexed[word]:
                    candidate_counts[idx] = candidate_counts.get(idx, 0) + 1
        
        if not candidate_counts:
            print(f"   No candidates found for keywords: {query_words}")
            return []
        
        print(f"   Found {len(candidate_counts)} candidate pairs")
        
        # Score all candidates
        sorted_candidates = sorted(candidate_counts.items(), key=lambda x: x[1], reverse=True)
        
        scored_results = []
        for idx, overlap_count in sorted_candidates[:200]:  # Score top 200
            qa = self.qa_pairs[idx]
            question_lower = qa['question'].lower()
            
            # String similarity
            similarity = SequenceMatcher(None, query_lower, question_lower).ratio()
            
            # Keyword match score
            keyword_score = overlap_count / len(query_words) if query_words else 0
            
            # Combined score (70% keywords, 30% similarity)
            final_score = (keyword_score * 7.0) + (similarity * 3.0)
            
            scored_results.append((final_score, qa))
        
        # Sort by score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Very low threshold - accept any reasonable match from dataset
        THRESHOLD = 0.5
        
        results = [qa for score, qa in scored_results if score >= THRESHOLD][:top_k]
        
        if results:
            top_score = scored_results[0][0]
            top_qa = scored_results[0][1]
            print(f"   ✅ Top match (score: {top_score:.2f}): '{top_qa['question'][:60]}...'")
        
        return results
    
    def get_response(self, query: str) -> str:
        """Get response from dataset only"""
        if not query or not query.strip():
            return "Please describe your medical question or symptoms."
        
        if not self.ready:
            return "Dataset is loading. Please wait..."
        
        print(f"\n🔍 Searching dataset for: '{query}'")
        start_time = time.time()
        
        try:
            # Search dataset
            matches = self._find_best_matches(query, top_k=5)
            
            elapsed = time.time() - start_time
            
            if matches:
                # Return the best match (first one)
                response = matches[0]['answer']
                print(f"   ✅ Found answer in {elapsed:.3f}s")
                return f"💊 {response}"
            else:
                print(f"   ⚠️  No matches found in {elapsed:.3f}s")
                # Only return this if we truly found nothing
                return (
                    "📊 I searched the medical database but didn't find a direct match for your query. "
                    "However, this doesn't mean your question isn't important. "
                    "Please consult a healthcare professional for accurate diagnosis and guidance."
                )
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error processing your query: {str(e)}"


# Keep SimpleMedicalChatbot for backward compatibility, but DON'T use it
class SimpleMedicalChatbot:
    """Deprecated - only for backward compatibility"""
    def get_response(self, query: str) -> str:
        return "Error: Use MedicalDatasetChatbot instead"


def warm_up_chatbot_on_startup():
    """Initialize chatbot on startup"""
    try:
        chatbot = MedicalDatasetChatbot()
        if chatbot.ready:
            print("✅ Chatbot ready!")
        else:
            print("❌ Chatbot failed to load dataset")
    except Exception as e:
        print(f"❌ Chatbot initialization error: {e}")


if __name__ == "__main__":
    print("Testing Pure Dataset Medical Chatbot...\n")
    
    test_queries = [
        "what is the normal temperature of human body",
        "my body temperature is high",
        "i have heavy fever",
        "normal body temperature",
        "fever",
        "cold",
        "chest pain",
    ]
    
    chatbot = MedicalDatasetChatbot()
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Q: {query}")
        print(f"{'-'*80}")
        response = chatbot.get_response(query)
        print(f"A: {response[:300]}...")
