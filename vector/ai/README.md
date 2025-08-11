# Adding New AI Providers

This guide explains how to add support for new AI providers (like Anthropic, Google, Azure, etc.) to the RegScout vector system.

## Overview

The system uses a factory pattern to support multiple AI providers. Each provider needs:
1. A model class implementing `BaseAIModel`
2. Registration with the `AIModelFactory`
3. Configuration support

## Step 1: Create the Provider Model Class

Create a new file in `vector/ai/` for your provider:

```python
# filepath: e:\02-regscout\vector\ai\anthropic.py
"""Anthropic Claude model implementation."""

from typing import Optional, Dict, Any
import anthropic
from .base import BaseAIModel
from ..config import Config
from ..exceptions import AIServiceError


class AnthropicModel(BaseAIModel):
    """Anthropic Claude model implementation."""

    def __init__(self, config: Config):
        """Initialize Anthropic model.
        
        Args:
            config: Configuration object
        """
        # Get model name from config
        model_name = config.ai_search_model_name  # or ai_answer_model_name
        super().__init__(model_name)
        
        self.config = config
        self.api_key = config.anthropic_api_key  # You'll need to add this to config
        self.max_tokens = config.ai_search_max_tokens
        self.temperature = config.ai_search_temperature
        self.provider = "anthropic"
        
        if not self.api_key:
            raise AIServiceError("Anthropic API key not found")
        
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except Exception as e:
            raise AIServiceError(f"Failed to initialize Anthropic client: {e}")

    def is_available(self) -> bool:
        """Check if Anthropic API is available."""
        try:
            # Simple test call to check API availability
            return bool(self.api_key and self.client)
        except Exception:
            return False

    def generate_response(self, prompt: str, system_prompt: str = "", 
                         max_tokens: Optional[int] = None, **kwargs) -> str:
        """Generate response using Anthropic API.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Generated response text
        """
        if not self.is_available():
            raise AIServiceError("Anthropic API not available")

        max_tokens = max_tokens or self.max_tokens
        temperature = kwargs.get('temperature', self.temperature)

        try:
            # Build the message
            messages = [{"role": "user", "content": prompt}]
            
            # Anthropic API call
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise AIServiceError(f"Anthropic API error: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "configured_max_tokens": self.max_tokens,
            "configured_temperature": self.temperature,
            "available": self.is_available()
        }

    def get_available_models(self):
        """Get a list of available models from the provider's API.
        
        Returns:
            List of model names/IDs available from the provider
        """
        try:
            # Implementation depends on provider's API
            # For Anthropic example:
            # return ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
            
            # For most providers, you'll need to call their API
            # to get the current list of available models
            pass
        except Exception as e:
            raise AIServiceError(f"Failed to fetch available models: {e}")
```

## Step 2: Register the Provider

Add your provider to the factory in `vector/ai/factory.py`:

```python
# filepath: e:\02-regscout\vector\ai\factory.py
"""AI Model Factory for creating different AI providers."""

from typing import Dict, Any, Type, List
from ..config import Config
from ..exceptions import AIServiceError
from .base import BaseAIModel
from .openai import OpenAIModel
from .anthropic import AnthropicModel  # Add this import


class AIModelFactory:
    """Factory for creating AI models from different providers."""
    
    # Registry of available providers
    _providers: Dict[str, Type[BaseAIModel]] = {
        "openai": OpenAIModel,
        "anthropic": AnthropicModel,  # Add your provider here
        # "google": GoogleModel,
        # "azure": AzureOpenAIModel,
    }
    
    # ... rest of the class remains the same
```

**Important**: Also update the CLI parser to include your new provider in the choices:

```python
# filepath: e:\02-regscout\vector\cli\parser.py
# In the models command parser section:
models_parser.add_argument(
    '--provider', '-p',
    choices=['openai', 'anthropic'],  # Add your provider here
    default='openai',
    help='AI provider to list models for (default: openai)'
)
```

## Step 3: Update Configuration Support

Add configuration properties to `vector/config.py`:

```python
# filepath: e:\02-regscout\vector\config.py
class Config:
    # ... existing code ...
    
    @property
    def anthropic_api_key(self) -> str:
        """Get Anthropic API key."""
        # Try environment variable first
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key
        
        # Try config file
        return self._config_data.get("anthropic", {}).get("api_key", "")
    
    # ... rest of existing properties ...
```

## Step 4: Update Configuration File

Add API key configuration to `config.yaml`:

```yaml
# filepath: e:\02-regscout\config.yaml
# Vector Configuration

# Embedding Model Settings
embedder:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"

# AI Model Settings - Multiple Models Support
ai_models:
  # Search model
  search:
    name: "claude-3-haiku-20240307"    # Anthropic model
    max_tokens: 1000
    temperature: 0.3
    provider: "anthropic"              # Use Anthropic for search
  
  # Answer model
  answer:
    name: "gpt-4o"                     # OpenAI model
    max_tokens: 4000
    temperature: 0.7
    provider: "openai"                 # Use OpenAI for answers

# API Keys (optional - prefer environment variables)
anthropic:
  api_key: null  # Set ANTHROPIC_API_KEY environment variable

# ... rest of config
```

## Step 5: Set Environment Variables

Set your API keys as environment variables:

```bash
# Windows
set ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Linux/Mac
export ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Step 6: Update Imports

Add your provider to `vector/ai/__init__.py`:

```python
# filepath: e:\02-regscout\vector\ai\__init__.py
"""AI module for vector system."""

from .base import BaseAIModel
from .openai import OpenAIModel
from .anthropic import AnthropicModel  # Add this
from .factory import AIModelFactory

__all__ = [
    'BaseAIModel',
    'OpenAIModel', 
    'AnthropicModel',  # Add this
    'AIModelFactory'
]
```

## Step 7: Install Dependencies

Add required packages to your requirements:

```bash
pip install anthropic
```

## Testing Your New Provider

Test your implementation:

```python
from vector.config import Config
from vector.ai.factory import AIModelFactory

# Load config
config = Config("config.yaml")

# Test creating your new provider
try:
    model = AIModelFactory.create_model(config, "search")
    print(f"✅ Successfully created {model.provider} model: {model.model_name}")
    
    # Test generation
    response = model.generate_response("Hello", "You are a helpful assistant")
    print(f"✅ Response: {response[:100]}...")
    
    # Test available models listing
    available_models = model.get_available_models()
    print(f"✅ Available models: {len(available_models)} models found")
    for i, model_name in enumerate(available_models[:5], 1):
        print(f"   {i}. {model_name}")
    
except Exception as e:
    print(f"❌ Error: {e}")
```

You can also test the models command in the CLI:

```bash
# List available models
python -m vector models --provider anthropic
python -m vector models -p anthropic
```

## Common Provider Examples

### Google Gemini
```python
# Model names: gemini-pro, gemini-pro-vision
# API: google.generativeai
# Key: GOOGLE_API_KEY
```

### Azure OpenAI
```python
# Model names: gpt-4, gpt-35-turbo
# API: openai with azure endpoint
# Keys: AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT
```

### Cohere
```python
# Model names: command, command-light
# API: cohere
# Key: COHERE_API_KEY
```

## Best Practices

1. **Environment Variables**: Always prefer environment variables for API keys
2. **Error Handling**: Implement proper error handling for API failures
3. **Model Info**: Provide comprehensive model information
4. **Testing**: Test both search and answer model types
5. **Documentation**: Update this guide when adding new providers
6. **Dependencies**: Keep provider-specific dependencies optional

## Troubleshooting

### Common Issues:

1. **Import Errors**: Make sure to install provider-specific packages
2. **API Key Issues**: Check environment variables and config file
3. **Model Names**: Verify model names match provider's API
4. **Rate Limits**: Implement retry logic for production use

### Debug Steps:

1. Test API key with provider's official examples
2. Check model availability and naming
3. Verify factory registration
4. Test with simple prompts first

## Available Models Command

The system includes a CLI command to list available models from any provider:

```bash
# List models from default provider (OpenAI)
python -m vector models

# List models from specific provider
python -m vector models --provider openai
python -m vector models --provider anthropic
python -m vector models -p google

# Get help for the models command
python -m vector models --help
```

This command calls the `get_available_models()` method on the provider's model class to fetch the current list of available models from their API.

### Example Output:
```
🤖 Available models for OPENAI:
   1. gpt-4
   2. gpt-4-turbo
   3. gpt-4o
   4. gpt-4o-mini
   5. gpt-3.5-turbo
   ...
```

## Future Enhancements

Consider adding:
- Retry logic with exponential backoff
- Usage tracking and cost monitoring
- Model-specific optimizations
- Streaming response support
- Async support for better performance

---

**Need help?** Check the existing `OpenAIModel` implementation as a reference, or refer to the provider's official documentation.