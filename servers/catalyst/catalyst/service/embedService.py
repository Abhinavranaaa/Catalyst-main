from catalyst.adapters.embed import EmbeddingServiceAdapter

class EmbeddingService:
    def __init__(self,provider=None):
        self.provider=provider or EmbeddingServiceAdapter()
    
    def embed_text(self, text: str):
        return self.provider.generate_embedding(text)
