#!/usr/bin/env python
# coding: utf-8
"""FetchX entry point: python run_server.py"""
import os
import sys

try:
    import certifi as _certifi
    _ca = _certifi.where()
    if _ca and os.path.exists(_ca):
        os.environ.setdefault('SSL_CERT_FILE', _ca)
        os.environ.setdefault('SSL_CERT_DIR', os.path.dirname(_ca))
except Exception:
    pass

import uvicorn


def main():
    host = os.environ.get('FETCHX_HOST', '127.0.0.1')
    port = int(os.environ.get('FETCHX_PORT', '8619'))
    print(f'FetchX listening on http://{host}:{port} '
          f'(downloads -> {os.environ.get("FETCHX_DOWNLOAD_DIR", "./downloads")})',
          flush=True)
    uvicorn.run('fetchx.server:app', host=host, port=port, log_level='info')


if __name__ == '__main__':
    sys.exit(main())
