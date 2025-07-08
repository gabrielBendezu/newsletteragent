import json
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime

from haystack import Document, Pipeline
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.converters import HTMLToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack.utils import Secret


@dataclass
class QdrantConfig:
    """Configuration for Qdrant connection"""
    url: str = "https://07d9c379-addb-4c4c-a4c6-5a6834c9f9aa.eu-central-1-0.aws.cloud.qdrant.io"
    api_key: Secret = Secret.from_env_var("QDRANT_API_KEY")
    collection_name: str = "newsletter_articles"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 384  # Dimension for all-MiniLM-L6-v2


class NewsletterQdrantStorage:
    def __init__(self, config: QdrantConfig = None):
        self.config = config or QdrantConfig()
        self.document_store = None
        self.newsletter_embedder = None
        self.query_embedder = None
        self.retriever = None
        self.indexing_pipeline = None
        self.document_writer = None
        self.html_converter = None
        self.cleaner = None
        self.splitter = None
        self._setup_components()
    
    def _setup_components(self):
        """Initialize Qdrant document store and processing components"""
        print(f"🔧 Setting up Qdrant connection...")
        
        # Initialize document store
        self.document_store = QdrantDocumentStore(
            url=self.config.url,
            api_key=self.config.api_key,
            index=self.config.collection_name,
            embedding_dim=self.config.embedding_dim,
            recreate_index=False,
            return_embedding=True,
            wait_result_from_api=True,
            similarity="cosine"
        )
        
        # Initialize processing components
        self.html_converter = HTMLToDocument()
        self.cleaner = DocumentCleaner(
            remove_empty_lines=True,
            remove_extra_whitespaces=True,
            remove_repeated_substrings=True
        )
        self.splitter = DocumentSplitter(
            split_by="sentence",
            split_length=500,
            split_overlap=50
        )
        
        # Initialize embedders
        self.newsletter_embedder = SentenceTransformersDocumentEmbedder(
            model=self.config.embedding_model,
            progress_bar=True
        )
        
        self.query_embedder = SentenceTransformersTextEmbedder(
            model=self.config.embedding_model,
            progress_bar=True
        )
        
        # Initialize retriever
        self.retriever = QdrantEmbeddingRetriever(
            document_store=self.document_store,
            top_k=5
        )
        
        # Create indexing pipeline
        self.indexing_pipeline = self._create_indexing_pipeline()
        
        print("✓ Qdrant components initialized")
    
    def _create_indexing_pipeline(self) -> Pipeline:
        """Create a pipeline for processing and indexing newsletters"""
        pipeline = Pipeline()
        
        # Add components
        pipeline.add_component("cleaner", self.cleaner)
        pipeline.add_component("splitter", self.splitter)
        pipeline.add_component("embedder", self.newsletter_embedder)
        pipeline.add_component("writer", self.document_store)
        
        # Connect components
        pipeline.connect("cleaner", "splitter")
        pipeline.connect("splitter", "embedder")
        pipeline.connect("embedder", "writer")
        
        return pipeline
    
    def _create_documents_from_newsletters(self, newsletters: List[Dict]) -> List[Document]:
        """Convert newsletter dictionaries to Haystack Documents"""
        documents = []
        
        for newsletter in newsletters:
            # Prepare content - prefer HTML, fall back to plain text
            if newsletter.get('content_html'):
                content = newsletter['content_html']
                content_type = "html"
            else:
                content = newsletter.get('content_plain', '')
                content_type = "plain"
            
            # If content is very short, include subject
            if len(content) < 100:
                content = f"{newsletter['subject']}. {content}"
            
            # Create comprehensive metadata
            metadata = {
                "message_id": newsletter['message_id'],
                "thread_id": newsletter['thread_id'],
                "subject": newsletter['subject'],
                "sender": newsletter['sender'],
                "sender_name": newsletter['sender_name'],
                "recipient": newsletter['recipient'],
                "date": newsletter['date'],
                "timestamp": newsletter['timestamp'],
                "newsletter_name": newsletter['newsletter_name'],
                "article_urls": newsletter['article_urls'],
                "labels": newsletter['labels'],
                "snippet": newsletter['snippet'],
                "content_type": content_type,
                "content_length": len(content),
                "url_count": len(newsletter.get('article_urls', [])),
                "processed_date": datetime.now().isoformat(),
                "primary_url": newsletter['article_urls'][0] if newsletter.get('article_urls') else None
            }
            
            # Create document
            document = Document(content=content, meta=metadata)
            documents.append(document)
        
        return documents
    
    def _process_html_content(self, documents: List[Document]) -> List[Document]:
        """Process HTML content using Haystack's HTML converter"""
        processed_docs = []
        
        for doc in documents:
            if doc.meta.get('content_type') == 'html':
                # Convert HTML to clean text
                html_result = self.html_converter.run(sources=[doc.content])
                if html_result.get('documents'):
                    # Update the document with cleaned content
                    cleaned_doc = html_result['documents'][0]
                    # Preserve original metadata
                    cleaned_doc.meta.update(doc.meta)
                    processed_docs.append(cleaned_doc)
                else:
                    # Fallback to original document
                    processed_docs.append(doc)
            else:
                processed_docs.append(doc)
        
        return processed_docs
    
    def check_document_exists(self, message_id: str) -> bool:
        """Check if document with given message_id already exists"""
        try:
            filters = {
                "field": "message_id",
                "operator": "==",
                "value": message_id
            }
            
            results = self.document_store.filter_documents(filters=filters)
            return len(results) > 0
            
        except Exception as e:
            print(f"⚠️  Error checking document existence: {e}")
            return False
    
    def store_newsletters(self, newsletters: List[Dict], skip_existing: bool = True) -> Dict:
        """
        Store newsletters in Qdrant using Haystack pipeline
        
        Args:
            newsletters: List of newsletter dictionaries
            skip_existing: Whether to skip newsletters that already exist
            
        Returns:
            Dictionary with storage statistics
        """
        print(f"📦 Processing {len(newsletters)} newsletters for storage...")
        
        newsletters_to_process = []
        skipped_count = 0
        
        # Filter out existing newsletters
        for newsletter in newsletters:
            message_id = newsletter['message_id']
            
            if skip_existing and self.check_document_exists(message_id):
                print(f"⏭️  Skipping existing newsletter: {newsletter['subject']}")
                skipped_count += 1
                continue
            
            newsletters_to_process.append(newsletter)
            print(f"📄 Prepared: {newsletter['subject']}")
        
        if not newsletters_to_process:
            print("ℹ️  No new documents to store")
            return {
                "total_processed": len(newsletters),
                "stored": 0,
                "skipped": skipped_count,
                "errors": 0
            }
        
        try:
            # Create documents from newsletters
            documents = self._create_documents_from_newsletters(newsletters_to_process)
            
            # Process HTML content
            documents = self._process_html_content(documents)
            
            # Run through indexing pipeline
            print(f"🔄 Processing {len(documents)} documents through pipeline...")
            result = self.indexing_pipeline.run({"cleaner": {"documents": documents}})
            
            stored_count = len(result.get("writer", {}).get("documents_written", []))
            print(f"✅ Successfully stored {stored_count} documents")
            
            return {
                "total_processed": len(newsletters),
                "stored": stored_count,
                "skipped": skipped_count,
                "errors": 0
            }
            
        except Exception as e:
            print(f"❌ Error storing documents: {e}")
            return {
                "total_processed": len(newsletters),
                "stored": 0,
                "skipped": skipped_count,
                "errors": len(newsletters_to_process)
            }
    
    def search_newsletters(self, query: str, filters: Dict = None, top_k: int = 5) -> List[Dict]:
        """Search newsletters using semantic search"""
        print(f"🔍 Searching for: '{query}'")
        
        try:
            # Generate query embedding
            query_embedding = self.query_embedder.run(text=query)["embedding"]
            
            # Set up retriever with filters if provided
            if filters:
                retriever = QdrantEmbeddingRetriever(
                    document_store=self.document_store,
                    filters=filters,
                    top_k=top_k
                )
            else:
                retriever = self.retriever
            
            # Perform search
            results = retriever.run(query_embedding=query_embedding)
            
            # Format results
            formatted_results = []
            for doc in results.get("documents", []):
                formatted_results.append({
                    "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                    "score": doc.score if hasattr(doc, 'score') else 0.0,
                    "metadata": doc.meta
                })
            
            print(f"✓ Found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error searching newsletters: {e}")
            return []
    
    def create_search_pipeline(self) -> Pipeline:
        """Create a pipeline for searching newsletters"""
        search_pipeline = Pipeline()
        
        # Add components
        search_pipeline.add_component("embedder", self.query_embedder)
        search_pipeline.add_component("retriever", self.retriever)
        
        # Connect components
        search_pipeline.connect("embedder.embedding", "retriever.query_embedding")
        
        return search_pipeline
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the stored newsletters"""
        try:
            all_docs = self.document_store.filter_documents()
            total_count = len(all_docs)
            
            if total_count == 0:
                return {"total_documents": 0}
            
            # Get newsletter name distribution
            newsletter_counts = {}
            for doc in all_docs:
                newsletter_name = doc.meta.get('newsletter_name', 'Unknown')
                newsletter_counts[newsletter_name] = newsletter_counts.get(newsletter_name, 0) + 1
            
            # Get date range
            timestamps = [doc.meta.get('timestamp', 0) for doc in all_docs if doc.meta.get('timestamp')]
            date_range = {
                "earliest": datetime.fromtimestamp(min(timestamps)).isoformat() if timestamps else None,
                "latest": datetime.fromtimestamp(max(timestamps)).isoformat() if timestamps else None
            }
            
            return {
                "total_documents": total_count,
                "newsletter_distribution": newsletter_counts,
                "date_range": date_range
            }
            
        except Exception as e:
            print(f"❌ Error getting collection stats: {e}")
            return {"error": str(e)}
    
    def delete_newsletter(self, message_id: str) -> bool:
        """Delete a newsletter by message_id"""
        try:
            filters = {
                "field": "message_id",
                "operator": "==",
                "value": message_id
            }
            
            docs_to_delete = self.document_store.filter_documents(filters=filters)
            
            if not docs_to_delete:
                print(f"⚠️  No document found with message_id: {message_id}")
                return False
            
            self.document_store.delete_documents([doc.id for doc in docs_to_delete])
            print(f"✅ Deleted newsletter: {message_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting newsletter: {e}")
            return False


def load_newsletters_from_json(filename: str) -> List[Dict]:
    """Load newsletters from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            newsletters = json.load(f)
        print(f"✓ Loaded {len(newsletters)} newsletters from {filename}")
        return newsletters
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return []


def main():
    """Test the improved storage system"""
    storage = NewsletterQdrantStorage()
    
    # Load newsletters from JSON
    newsletters = load_newsletters_from_json('newsletters.json')
    
    if newsletters:
        # Store newsletters
        stats = storage.store_newsletters(newsletters)
        print(f"\n📊 Storage Statistics:")
        print(f"   Total processed: {stats['total_processed']}")
        print(f"   Stored: {stats['stored']}")
        print(f"   Skipped: {stats['skipped']}")
        print(f"   Errors: {stats['errors']}")
        
        # Get collection stats
        collection_stats = storage.get_collection_stats()
        print(f"\n📈 Collection Statistics:")
        print(f"   Total documents: {collection_stats.get('total_documents', 0)}")
        
        if 'newsletter_distribution' in collection_stats:
            print("   Newsletter distribution:")
            for newsletter, count in collection_stats['newsletter_distribution'].items():
                print(f"     {newsletter}: {count}")
        
        # Test search
        print("\n🔍 Testing search...")
        results = storage.search_newsletters("artificial intelligence", top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"\n   Result {i} (score: {result['score']:.3f}):")
            print(f"   Newsletter: {result['metadata']['newsletter_name']}")
            print(f"   Subject: {result['metadata']['subject']}")
            print(f"   Content preview: {result['content'][:200]}...")
    else:
        print("No newsletters to process. Run gmail_fetcher.py first.")


if __name__ == "__main__":
    main()