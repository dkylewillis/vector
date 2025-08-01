"""AI model integrations for the query engine."""

from .base import BaseAIModel
from .openai_model import OpenAIModel
from .factory import AIModelFactory

# Register all available models
AIModelFactory.register_model('openai', OpenAIModel)
AIModelFactory.register_model('gpt', OpenAIModel)
AIModelFactory.register_model('gpt-3.5-turbo', OpenAIModel)
AIModelFactory.register_model('gpt-4', OpenAIModel)

__all__ = ['BaseAIModel', 'OpenAIModel', 'AIModelFactory']