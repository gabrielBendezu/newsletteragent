import os
import logging

from gpt_interface.rag_api import create_app
from dotenv import load_dotenv

app = create_app()

if __name__ == '__main__':
    load_dotenv()

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    # logger.info(f"Starting Gmail Newsletter API server on {host}:{port}")
    # logger.info(f"Health check: http://{host}:{port}/health") 
    # logger.info(f"API endpoints: http://{host}:{port}/api/emails")

    print(f"Running server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)