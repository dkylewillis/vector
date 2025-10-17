"""Gradio UI for Vector."""

from .service import VectorWebService

__all__ = ['VectorWebService', 'create_gradio_app']

# Import on demand to avoid requiring gradio if just using the service
def create_gradio_app():
    """Create Gradio app - imports gradio components on demand."""
    from .app import create_gradio_app as _create_app
    return _create_app()

