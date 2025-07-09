import os
import logging
from datetime import datetime
from typing import List

from flask import Flask, request, jsonify
from flask_cors import CORS

from ..models import RAGChunk

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
# limiter = Limiter(
#     app,
#     key_func=get_remote_address,
#     default_limits=["200 per day", "50 per hour"]
# )

# def require_auth(f):
#     """Decorator to require API token authentication"""
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if not API_TOKEN or API_TOKEN == 'your-default-token':
#             # Skip auth if no token is configured
#             return f(*args, **kwargs)
        
#         auth_header = request.headers.get('Authorization')
#         if not auth_header or not auth_header.startswith('Bearer '):
#             return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
#         token = auth_header.split(' ')[1]
#         if token != API_TOKEN:
#             return jsonify({'error': 'Invalid API token'}), 401
        
#         return f(*args, **kwargs)
#     return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'service': 'Gmail Newsletter API'
    })

@app.route('/api/newsletter-context', methods=['GET'])
#@limiter.limit("30 per minute")
#@require_auth
def query_rag():
    """Query RAG system and return contextual results"""
    try:
        # Parse query parameters
        user_query = request.args.get('user_query')
        if not user_query:
            return jsonify({'error': 'Missing required parameter: user_query'}), 400

        logger.info(f"Received query: {user_query}")

        from retrieval_pipeline.rag_client import query_rag_system  

        context: List[RAGChunk] = query_rag_system(user_query=user_query, top_k=5)

        # def query_rag_system(user_query: str) -> List[RAGChunk]: (inside rag_client)

        if not context:
            return jsonify({
                'success': False,
                'error': 'No relevant context found',
                'user_query': user_query
            }), 404

        return jsonify({
            'success': True,
            'user_query': user_query,
            'context': context,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error querying RAG system: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to query RAG system',
            'message': str(e)
        }), 500

## Tests
# test_context: List[RAGChunk] = [
#     {
#         "id": "1",
#         "content": "Bananas have become spherical according to Dr Ibrahim.",
#         "subine": "Bananas",
#         "author": "Alice",
#         "sourceUrl": "https://example.com/article1",
#         "publishedAt": "2023-10-01T12:00:00Z",
#         "tags": ["tag1", "tag2"]
#     },
#     {
#         "id": "2",
#         "content": "Oranges have become cubes according to the EP.",
#         "headline": "Oranges",
#         "author": "Bob",
#         "sourceUrl": "https://example.com/article2",
#         "publishedAt": "2023-10-02T15:30:00Z",
#         "tags": ["tag3"]
#     },
#     {
#         "id": "3",
#         "content": "Apples have turned blue according to Macnimmmir.",
#         "headline": "Apples",
#         "author": "Carol",
#         "sourceUrl": "https://example.com/article3",
#         "publishedAt": "2023-10-03T09:45:00Z",
#         "tags": None
#     }
# ]

@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Handle rate limit exceeded"""
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.'
    }), 429

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

def create_app():
    return app