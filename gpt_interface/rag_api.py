import os
import logging
from datetime import datetime
from typing import List

from flask import Flask, request, jsonify
from flask_cors import CORS

from rag_chunk import RAGChunk

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
        question = request.args.get('question')
        if not question:
            return jsonify({'error': 'Missing required parameter: question'}), 400

        logger.info(f"Received query: {question}")

        from rag_pipeline.rag_client import query_rag_system  

        context: List[RAGChunk] = query_rag_system(question)
        # Chunk = {
        # "id": "chunk_xyz123",
        # "content": "Here's a key insight from the newsletter...",
        # "headline": "AI in July: What’s Next",
        # "author": "Tech Digest",
        # "sourceUrl": "https://techdigest.substack.com/p/ai-in-july",
        # "publishedAt": "2025-07-06T08:30:00Z",
        # "tags": ["AI", "newsletter", "trends"]
        # }

        # def query_rag_system(question: str) -> List[RAGChunk]: (inside rag_client)

        if not context:
            return jsonify({
                'success': False,
                'error': 'No relevant context found',
                'question': question
            }), 404

        return jsonify({
            'success': True,
            'question': question,
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