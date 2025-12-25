#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

DEFAULT_PORT = int(os.environ.get('DENNIK_PORT', '5005'))

if __name__ == '__main__':
    app = create_app()
    # Run on configurable port so CLI, launcher, and docs stay in sync
    app.run(debug=True, host='0.0.0.0', port=DEFAULT_PORT)