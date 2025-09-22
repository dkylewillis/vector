"""Web interface for Vector."""

from .service import VectorWebService

__all__ = ['VectorWebService']

# Gradio-dependent components are imported on demand
def create_vector_app():
    """Create vector app - imports gradio on demand."""
    from .main import create_vector_app
    return create_vector_app()

def main():
    """Main entry point - imports gradio on demand.""" 
    from .main import main
    return main()
