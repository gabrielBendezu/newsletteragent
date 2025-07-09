from haystack import Pipeline, Document
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.embedders import OpenAIDocumentEmbedder
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from typing import List

from qdrant_config import QdrantConfig
from newsletter_interface.newsletter import NewsletterEmail


def create_document_store() -> QdrantDocumentStore:
    """Create and configure the Qdrant document store."""
    config = QdrantConfig
    return QdrantDocumentStore(
        url=config.url,
        api_key=config.api_key,
        index=config.collection_name,
        embedding_dim=config.embedding_dim,
        recreate_index=False,
        return_embedding=True,
        wait_result_from_api=True,
        similarity="cosine"
    )


def newsletter_to_document(newsletter: NewsletterEmail) -> Document:
    """Convert a newsletter to a Haystack Document."""
    return Document(
        content=newsletter.content_plain,
        meta={
            "primary_url": newsletter.primary_url,
            "date": newsletter.date,
            "subject": newsletter.subject,
            "newsletter_name": newsletter.newsletter_name,
            "message_id": newsletter.message_id,
        }
    )


def create_indexing_pipeline(document_store: QdrantDocumentStore) -> Pipeline:
    """Create the document indexing pipeline."""
    # Components
    document_cleaner = DocumentCleaner()
    document_splitter = DocumentSplitter(
        split_by="word", 
        split_length=512, 
        split_overlap=32
    )
    document_embedder = OpenAIDocumentEmbedder(
        model="text-embedding-3-small" 
    )
    document_writer = DocumentWriter(
        document_store=document_store, 
        policy=DuplicatePolicy.OVERWRITE
    )

    # Pipeline assembly
    pipeline = Pipeline()
    pipeline.add_component("cleaner", document_cleaner)
    pipeline.add_component("splitter", document_splitter)
    pipeline.add_component("embedder", document_embedder)
    pipeline.add_component("writer", document_writer)

    # Connections
    pipeline.connect("cleaner", "splitter")
    pipeline.connect("splitter", "embedder")
    pipeline.connect("embedder", "writer")

    return pipeline


def store_newsletters(newsletters: List[NewsletterEmail]) -> None:
    """Store newsletters in the vector database."""
    if not newsletters:
        return
    
    # Convert newsletters to documents
    docs = [newsletter_to_document(newsletter) for newsletter in newsletters]
    
    # Create document store and pipeline
    document_store = create_document_store()
    pipeline = create_indexing_pipeline(document_store)
    
    # Process documents
    pipeline.run({"cleaner": {"documents": docs}})