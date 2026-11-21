from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue 

from ai_apps.settings import collection_name, embed_dim

class QdrantStorage: 
    def __init__(self, url='http://localhost:6333', collection=None, dim=None): 
        self.client = QdrantClient(url=url, timeout=30)  
        self.collection = collection or collection_name()
        dim = dim or embed_dim()
        if not self.client.collection_exists(self.collection): 
            self.client.create_collection(
                collection_name=self.collection, 
                vectors_config= VectorParams(size=dim, distance=Distance.COSINE)
            ) 
        else:
            size = self.client.get_collection(self.collection).config.params.vectors.size
            if size != dim:
                raise RuntimeError(f"collection '{self.collection}' stores {size}-dim vectors but the embedding model makes {dim}-dim ones; check EMBED_MODEL / EMBED_DIM in .env")

    def upsert(self, ids, vectors, payloads): 
        points = [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]   
        self.client.upsert(self.collection, points=points)

    def delete_source(self, source: str):
        #re-uploading a pdf must replace it, not leave stale chunks of the old version behind
        self.client.delete(
            self.collection,
            points_selector=Filter(must=[FieldCondition(key='source', match=MatchValue(value=source))]),
        )

    def search(self, query_vector, token:int = 5): 
        result = self.client.query_points(
            collection_name=self.collection, 
            query= query_vector, 
            limit = token, 
            with_payload=True
        )
        context = [] 
        sources = []

        for r in result.points: 
            payload = getattr(r, 'payload', None) or {}
            context.append(payload.get('text', ''))
            page = payload.get('page')
            label = f"{payload.get('source', '')} (p.{page})" if page else payload.get('source', '')
            if label not in sources:
                sources.append(label)
        return {'context': context, 'sources': sources}
