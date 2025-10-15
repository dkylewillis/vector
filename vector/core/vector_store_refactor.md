# Vector store abstraction and flexible search refactor

Goals

- Decouple Qdrant from app logic via a minimal, stable interface (ABC).
- Add a provider-agnostic search request/DSL to support complex filtering and future search modes.
- Move complex search composition (e.g., chunk windows) out of the vector store into utilities/services.
- Keep a compatibility path while migrating SearchService/Retriever.
- Optional: add an ergonomic “operator sugar” layer that compiles to the same DSL.

High-level plan

1) Introduce a provider-agnostic search DSL (requests, responses, filters).
2) Define BaseVectorStore ABC using that DSL.
3) Implement a Qdrant adapter that translates DSL → Qdrant filters.
4) Add a provider factory (env/config selectable).
5) Replace current vector_store.py with a thin facade that delegates to the provider (and keeps legacy methods temporarily).
6) Move get_chunk_window into a utility built on top of the DSL search.
7) Migrate SearchService/Retriever to the new API (gradually).
8) (Optional) Add an operator “sugar” layer for concise filter composition and window specs.

---

## Chunk position metadata (recommended)

Avoid relying on parsing positions from IDs (e.g., "chunk_42"). Instead, store explicit ordering metadata in each chunk's payload so windows and sequences are provider-agnostic and fast:

- document_id: string (required)
- chunk_index: int (required, 0-based, unique per document)
- char_start, char_end: ints (optional; original text offsets)
- token_start, token_end: ints (optional; if using token offsets)
- section_id: string and section_index: int (optional; structural grouping)
- version: string/int (optional; ingestion run identifier)

Performance (Qdrant): create payload indexes for fields you filter on (run once per collection):

```python
# Example index creation (pseudo-code; adapt to your Qdrant client setup)
client.create_payload_index(collection_name, field_name="document_id", field_schema={"type": "keyword"})
client.create_payload_index(collection_name, field_name="chunk_index", field_schema={"type": "integer"})
```

Migration tips:

- Backfill chunk_index for existing data by scanning each document's chunks in order and writing chunk_index to payload.
- Update your chunker/ingestion to always emit chunk_index (and offsets if useful).
- Replace any logic that parses positions from IDs with reads of chunk_index.

## 1) Add the search DSL

Single flexible entry: SearchRequest with optional vector and a composable filter AST. Provider-agnostic return shape: SearchResponse with Hit list.

```python
# vector/core/search/dsl.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

# Filter AST (provider-agnostic)
class FilterExpr(BaseModel):
    pass

class And(FilterExpr):
    all: List[FilterExpr]

class Or(FilterExpr):
    any: List[FilterExpr]

class Not(FilterExpr):
    expr: FilterExpr

class FieldEquals(FilterExpr):
    key: str
    value: Union[str, int, float, bool]

class FieldIn(FilterExpr):
    key: str
    values: List[Union[str, int, float, bool]]

class RangeFilter(FilterExpr):
    key: str
    gt: Optional[float] = None
    gte: Optional[float] = None
    lt: Optional[float] = None
    lte: Optional[float] = None

# Flexible search request/response
class SearchRequest(BaseModel):
    collection: str
    vector: Optional[List[float]] = None   # Optional: filter-only if None
    top_k: int = 10
    filter: Optional[FilterExpr] = None
    include_payload: bool = True
    include_vector: bool = False           # Not all providers support this

class Hit(BaseModel):
    id: Union[str, int]
    score: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None
    vector: Optional[List[float]] = None

class SearchResponse(BaseModel):
    hits: List[Hit]
```

---

## 2) Add a minimal BaseVectorStore ABC

No provider-specific types. One flexible search method using the DSL.

```python
# vector/core/stores/base.py
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from ..search.dsl import SearchRequest, SearchResponse

class DistanceType(str, Enum):
    COSINE = "cosine"
    DOT = "dot"
    EUCLIDEAN = "euclidean"

class BaseVectorStore(ABC):
    @abstractmethod
    def create_collection(self, collection_name: str, vector_size: int, distance: DistanceType = DistanceType.COSINE) -> None: ...
    @abstractmethod
    def delete_collection(self, name: str) -> None: ...
    @abstractmethod
    def list_collections(self) -> List[str]: ...
    @abstractmethod
    def upsert(self, collection_name: str, point_id: Union[str, int], vector: List[float], payload: Dict[str, Any]) -> None: ...
    @abstractmethod
    def search(self, request: SearchRequest) -> SearchResponse: ...
```

---

## 3) Implement the Qdrant provider (adapter)

Translate the DSL FilterExpr → Qdrant Filter. Support vector search and filter-only scans (via scroll).

```python
# vector/core/stores/qdrant_store.py
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance as QDistance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchAny,
    MatchValue,
    Range,
)

from .base import BaseVectorStore, DistanceType
from ..search.dsl import SearchRequest, SearchResponse, Hit, FilterExpr, And, Or, Not, FieldEquals, FieldIn, RangeFilter

def _map_distance(d: DistanceType) -> QDistance:
    if d == DistanceType.COSINE:
        return QDistance.COSINE
    if d == DistanceType.DOT:
        return QDistance.DOT
    if d == DistanceType.EUCLIDEAN:
        return QDistance.EUCLID
    return QDistance.COSINE

class QdrantVectorStore(BaseVectorStore):
    def __init__(self, *, db_path: Optional[str] = None, url: Optional[str] = None, api_key: Optional[str] = None):
        self.db_path = db_path
        self.url = url
        self.api_key = api_key

    @contextmanager
    def _client(self) -> Generator[QdrantClient, None, None]:
        client = QdrantClient(url=self.url, api_key=self.api_key) if self.url else QdrantClient(path=self.db_path)
        try:
            yield client
        finally:
            client.close()

    def create_collection(self, collection_name: str, vector_size: int, distance: DistanceType = DistanceType.COSINE) -> None:
        with self._client() as client:
            if client.collection_exists(collection_name):
                return
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=_map_distance(distance)),
            )

    def delete_collection(self, name: str) -> None:
        with self._client() as client:
            if client.collection_exists(name):
                client.delete_collection(name)

    def list_collections(self) -> List[str]:
        with self._client() as client:
            return [c.name for c in client.get_collections().collections]

    def upsert(self, collection_name: str, point_id: Union[str, int], vector: List[float], payload: Dict[str, Any]) -> None:
        with self._client() as client:
            if not client.collection_exists(collection_name):
                raise ValueError(f"Collection {collection_name} does not exist.")
            client.upsert(collection_name=collection_name, points=[PointStruct(id=point_id, vector=vector, payload=payload)])

    def search(self, request: SearchRequest) -> SearchResponse:
        q_filter = self._to_qdrant_filter(request.filter) if request.filter else None
        hits: List[Hit] = []
        with self._client() as client:
            if request.vector is None:
                points, _ = client.scroll(
                    collection_name=request.collection,
                    limit=request.top_k,
                    with_payload=request.include_payload,
                    scroll_filter=q_filter,
                )
                for p in points:
                    hits.append(Hit(id=p.id, score=None, payload=p.payload if request.include_payload else None))
            else:
                results = client.search(
                    collection_name=request.collection,
                    query_vector=request.vector,
                    limit=request.top_k,
                    query_filter=q_filter,
                    with_payload=request.include_payload,
                )
                for r in results:
                    hits.append(Hit(id=r.id, score=float(r.score) if hasattr(r, "score") else None, payload=r.payload if request.include_payload else None))
        return SearchResponse(hits=hits)

    def _to_qdrant_filter(self, expr: FilterExpr) -> Filter:
        if isinstance(expr, And):
            parts = [self._to_qdrant_filter(e) for e in expr.all]
            return self._merge_filters(must=parts)
        if isinstance(expr, Or):
            parts = [self._to_qdrant_filter(e) for e in expr.any]
            return self._merge_filters(should=parts)
        if isinstance(expr, Not):
            inner = self._to_qdrant_filter(expr.expr)
            return self._merge_filters(must_not=[inner])
        if isinstance(expr, FieldEquals):
            return Filter(must=[FieldCondition(key=expr.key, match=MatchValue(value=expr.value))])
        if isinstance(expr, FieldIn):
            return Filter(must=[FieldCondition(key=expr.key, match=MatchAny(any=expr.values))])
        if isinstance(expr, RangeFilter):
            rng = Range(gt=expr.gt, gte=expr.gte, lt=expr.lt, lte=expr.lte)
            return Filter(must=[FieldCondition(key=expr.key, range=rng)])
        return Filter(must=[])

    def _merge_filters(self, must: Optional[List[Filter]] = None, should: Optional[List[Filter]] = None, must_not: Optional[List[Filter]] = None) -> Filter:
        m, s, n = [], [], []
        for fl in must or []:
            m.extend(getattr(fl, "must", []) or [])
            s.extend(getattr(fl, "should", []) or [])
            n.extend(getattr(fl, "must_not", []) or [])
        for fl in should or []:
            s.extend(getattr(fl, "must", []) or [])
            s.extend(getattr(fl, "should", []) or [])
            n.extend(getattr(fl, "must_not", []) or [])
        for fl in must_not or []:
            n.extend(getattr(fl, "must", []) or [])
            n.extend(getattr(fl, "should", []) or [])
            n.extend(getattr(fl, "must_not", []) or [])
        return Filter(must=m or None, should=s or None, must_not=n or None)
```

---

## 4) Add a provider factory

Select provider via config/env (VECTOR_STORE_PROVIDER), default to qdrant.

```python
# vector/core/stores/factory.py
import os
from typing import Optional
from .base import BaseVectorStore
from .qdrant_store import QdrantVectorStore

def create_store(provider: Optional[str] = None, *, db_path: Optional[str] = None, url: Optional[str] = None, api_key: Optional[str] = None) -> BaseVectorStore:
    name = (provider or os.getenv("VECTOR_STORE_PROVIDER") or "qdrant").lower()
    if name == "qdrant":
        return QdrantVectorStore(db_path=db_path, url=url, api_key=api_key)
    if name == "faiss":
        raise NotImplementedError("FAISS provider not implemented yet.")
    if name == "pinecone":
        raise NotImplementedError("Pinecone provider not implemented yet.")
    raise ValueError(f"Unknown vector store provider: {name}")
```

---

## 5) Refactor vector_store.py into a thin facade

Delegates to a BaseVectorStore created by the factory. Exposes search_advanced (DSL) and keeps legacy methods temporarily.

```python
# vector/core/vector_store.py
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, PrivateAttr
from ..config import Config
from .stores.base import BaseVectorStore, DistanceType
from .stores.factory import create_store
from .search.dsl import SearchRequest, SearchResponse

_config = Config()

class VectorStore(BaseModel):
    provider_name: str = Field(default="qdrant")
    db_path: Optional[str] = Field(default_factory=lambda: _config.vector_db_path)
    url: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)

    _provider: BaseVectorStore = PrivateAttr(default=None)

    class Config:
        arbitrary_types_allowed = True

    def _get(self) -> BaseVectorStore:
        if self._provider is None:
            self._provider = create_store(self.provider_name, db_path=self.db_path, url=self.url, api_key=self.api_key)
        return self._provider

    # New flexible search
    def search_advanced(self, request: SearchRequest) -> SearchResponse:
        return self._get().search(request)

    # CRUD ops
    def create_collection(self, collection_name: str, vector_size: int, distance: Union[str, DistanceType] = DistanceType.COSINE) -> None:
        d = DistanceType(distance) if isinstance(distance, str) else distance
        self._get().create_collection(collection_name, vector_size, d)

    def delete_collection(self, name: str) -> None:
        self._get().delete_collection(name)

    def list_collections(self) -> List[str]:
        return self._get().list_collections()

    def upsert(self, collection_name: str, point_id: Union[str, int], vector: List[float], payload: Dict[str, Any]) -> None:
        self._get().upsert(collection_name, point_id, vector, payload)

    # Legacy helper (optional)
    def insert(self, collection_name: str, point_id: Union[str, int], vector: List[float], payload: Dict[str, Any]) -> None:
        self.upsert(collection_name, point_id, vector, payload)
```

---

## 6) Move chunk window to a utility

Implement on top of search_advanced using filter-only requests and explicit chunk_index.

```python
# vector/core/search/utils.py
from __future__ import annotations
from typing import List
from .dsl import SearchRequest, And, FieldEquals, RangeFilter, Hit
from ..vector_store import VectorStore

def get_chunk_window(
    store: VectorStore,
    *,
    collection: str,
    document_id: str,
    center_index: int,
    window: int = 2,
) -> List[Hit]:
    start = max(0, center_index - window)
    end = center_index + window

    flt = And(all=[
        FieldEquals(key="document_id", value=document_id),
        RangeFilter(key="chunk_index", gte=start, lte=end),
    ])

    resp = store.search_advanced(SearchRequest(
        collection=collection,
        vector=None,              # filter-only
        top_k=(2 * window + 1),
        filter=flt,
        include_payload=True,
    ))

    return sorted(
        resp.hits,
        key=lambda h: (h.payload or {}).get("chunk_index", 10**9),
    )
```

---

## 7) Wire up SearchService/Retriever to the DSL

- Inject VectorStore (or BaseVectorStore) into SearchService.
- Build SearchRequest with:
  - vector: query embedding (if vector search)
  - top_k
  - filter: FieldIn("document_id", document_ids) and/or other DSL filters.
- For “window” behavior, call search.utils.get_chunk_window after the initial hits.

Example usage

- Basic vector search with a document filter:

```python
from vector.core.vector_store import VectorStore
from vector.core.search.dsl import SearchRequest, FieldIn

store = VectorStore(provider_name="qdrant")  # or env VECTOR_STORE_PROVIDER
req = SearchRequest(
    collection="docs",
    vector=[0.1, 0.2, 0.3],     # your embedding
    top_k=12,
    filter=FieldIn(key="document_id", values=["doc_1", "doc_2"]),
)
resp = store.search_advanced(req)
for hit in resp.hits:
    print(hit.id, hit.score, hit.payload)
```

- Chunk window:

```python
from vector.core.search.utils import get_chunk_window

# Suppose you have a center hit from a prior query
center_idx = (resp.hits[0].payload or {}).get("chunk_index", 0)

window_hits = get_chunk_window(
    store,
    collection="docs",
    document_id="doc_1",
    center_index=center_idx,
    window=2,
)
```

---

## 8) (Optional) Operator “sugar” layer (experimental)

Add an ergonomic, operator-overloaded layer that compiles to the same DSL AST. This improves readability while keeping providers unchanged.

- Field proxy with boolean ops and comparisons: F.user_id == "u1", F.source.isin([...]), (F.ts >= a) & (F.ts < b), ~(F.archived == True)
- Window spec via slicing: `around("chunk_42")[-2:2]` means “2 left, 2 right” around the center chunk.

```python
# vector/core/search/sugar.py
from __future__ import annotations
from typing import Iterable, Tuple
from .dsl import (
    FilterExpr, And, Or, Not, FieldEquals, FieldIn, RangeFilter,
)

class Expr:
    def __init__(self, node: FilterExpr): self._node = node
    def to_dsl(self) -> FilterExpr: return self._node
    def __and__(self, other: "Expr") -> "Expr": return Expr(And(all=[self.to_dsl(), ensure_filter(other)]))
    def __or__(self, other: "Expr") -> "Expr": return Expr(Or(any=[self.to_dsl(), ensure_filter(other)]))
    def __invert__(self) -> "Expr": return Expr(Not(expr=self.to_dsl()))
    def __repr__(self) -> str: return f"Expr({self._node!r})"

class Field(Expr):
    def __init__(self, name: str):
        self.name = name
        super().__init__(FieldEquals(key=name, value=None))  # placeholder
    def __eq__(self, value) -> Expr: return Expr(FieldEquals(key=self.name, value=value))  # type: ignore[override]
    def isin(self, values: Iterable) -> Expr: return Expr(FieldIn(key=self.name, values=list(values)))
    def __lt__(self, value) -> Expr: return Expr(RangeFilter(key=self.name, lt=value))    # type: ignore[override]
    def __le__(self, value) -> Expr: return Expr(RangeFilter(key=self.name, lte=value))  # type: ignore[override]
    def __gt__(self, value) -> Expr: return Expr(RangeFilter(key=self.name, gt=value))   # type: ignore[override]
    def __ge__(self, value) -> Expr: return Expr(RangeFilter(key=self.name, gte=value))  # type: ignore[override]
    def __repr__(self) -> str: return f"Field('{self.name}')"

class FieldProxy:
    def __getattr__(self, name: str) -> Field: return Field(name)

F = FieldProxy()

def ensure_filter(expr_or_filter) -> FilterExpr:
    if isinstance(expr_or_filter, Expr): return expr_or_filter.to_dsl()
    if isinstance(expr_or_filter, FilterExpr): return expr_or_filter
    raise TypeError(f"Expected Expr or FilterExpr, got {type(expr_or_filter)!r}")

class WindowSpec:
    def __init__(self, center_chunk_id: str, left: int = 0, right: int = 0):
        self.center_chunk_id = center_chunk_id
        self.left, self.right = int(left), int(right)
    def __getitem__(self, s: slice) -> "WindowSpec":
        left = abs(s.start) if isinstance(s.start, int) else 0
        right = abs(s.stop) if isinstance(s.stop, int) else 0
        return WindowSpec(self.center_chunk_id, left=left, right=right)
    def __add__(self, other: "WindowSpec") -> "WindowSpec":
        if self.center_chunk_id != other.center_chunk_id:
            raise ValueError("Cannot merge windows with different centers")
        return WindowSpec(self.center_chunk_id, left=max(self.left, other.left), right=max(self.right, other.right))
    def to_tuple(self) -> Tuple[int, int]: return (self.left, self.right)
    def __repr__(self) -> str: return f"WindowSpec(center={self.center_chunk_id!r}, left={self.left}, right={self.right})"

def around(center_chunk_id: str) -> WindowSpec:
    return WindowSpec(center_chunk_id)
```

Sugar usage examples:

```python
from vector.core.vector_store import VectorStore
from vector.core.search.dsl import SearchRequest
from vector.core.search.sugar import F, around, ensure_filter

store = VectorStore(provider_name="qdrant")

# Filters with operators
flt = (F.document_id.isin(["doc_1", "doc_2"])
       & ((F.source == "wiki") | (F.source == "notion"))
       & ~(F.archived == True)
       & (F.created_ts >= 1_710_000_000))

req = SearchRequest(collection="docs", vector=[0.12, -0.07, 0.33], top_k=10, filter=ensure_filter(flt))
resp = store.search_advanced(req)

# Window spec
w = around("chunk_42")[-2:2]  # 2 left, 2 right
```

Recommended tests:

```python
# tests/test_search_sugar.py
import pytest
from vector.core.search.sugar import F, ensure_filter, around
from vector.core.search.dsl import And, Or, Not, FieldEquals, RangeFilter, FieldIn

def test_boolean_and_or_not():
    expr = ((F.ts >= 10) | (F.ts < 5)) & ~(F.archived == True)
    node = ensure_filter(expr)
    assert isinstance(node, And)
    left, right = node.all
    assert isinstance(left, Or)
    assert isinstance(right, Not)
    assert isinstance(left.any[0], RangeFilter)
    assert isinstance(left.any[1], RangeFilter)

def test_field_equals_and_in():
    expr = F.source == "wiki"
    node = ensure_filter(expr)
    assert isinstance(node, FieldEquals)
    expr2 = F.document_id.isin(["d1", "d2"])
    node2 = ensure_filter(expr2)
    assert isinstance(node2, FieldIn)

def test_window_merge_and_guard():
    w1 = around("chunk_42")[-2:0]
    w2 = around("chunk_42")[0:3]
    merged = w1 + w2
    assert merged.to_tuple() == (2, 3)
    with pytest.raises(ValueError):
        _ = around("c1")[-1:0] + around("c2")[0:1]
```

Notes

- Keep sugar optional and small; it must compile to the same DSL.
- Document operator precedence; encourage parentheses with &, |, ~.
- Provide both sugar and plain-DSL examples in docs.

---

## Migration notes

- Keep vector/core/vector_store.py legacy methods only as thin wrappers; prefer SearchRequest/Response going forward.
- Update SearchService to build DSL requests instead of passing provider-native filters.
- Remove VectorStore.get_chunk_window after migrating callers to search.utils.get_chunk_window.
- Consider deprecating VectorStore.search and search_documents in favor of search_advanced.
- Sugar is optional: unwrap with ensure_filter before calling providers.

---

## Configuration

- Choose provider:
  - Environment: set VECTOR_STORE_PROVIDER=qdrant
  - Or construct VectorStore(provider_name="qdrant", url=..., api_key=..., db_path=...)

- Dependencies: qdrant-client (pip install qdrant-client)
- Testing (optional sugar): pytest

---

## Testing checklist

- Unit test BaseVectorStore contract using a provider test suite (search, upsert, list/delete collections).
- Test DSL → Qdrant filter translation: equals, in, range, AND/OR/NOT composition.
- Test filter-only scans (vector=None) and large top_k handling.
- Test chunk window utility using chunk_index with realistic payloads.
- Validate backfilled chunk_index correctness (contiguous, unique per document).
- If using Qdrant, verify payload indexes improve range-filter performance.
- Test sugar layer parity with DSL (golden cases) and window spec behavior.

---

## Extending with new providers

- Implement BaseVectorStore for the new backend (e.g., PineconeVectorStore).
- Map DSL filters to the provider’s native query constructs.
- Register it in stores/factory.py.
- Ensure SearchService/Retriever code remains unchanged (they only use the DSL).

---

## Refactor task list (ordered)

- [ ] Add vector/core/search/dsl.py
- [ ] Add vector/core/stores/base.py
- [ ] Add vector/core/stores/qdrant_store.py
- [ ] Add vector/core/stores/factory.py
- [ ] Replace vector/core/vector_store.py with the thin facade (keep legacy wrappers)
- [ ] Add vector/core/search/utils.py and migrate get_chunk_window callers
- [ ] Refactor SearchService to use SearchRequest/Response
- [ ] Update Retriever pipeline steps to build DSL filters (FieldIn for document_ids, etc.)
- [ ] Add tests for provider adapter and DSL translations
- [ ] Document provider selection via VECTOR_STORE_PROVIDER
- [ ] (Optional) Add vector/core/search/sugar.py and tests/test_search_sugar.py
- [ ] (Optional) Update docs with sugar usage and caveats
