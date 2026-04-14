from abc import ABC, abstractmethod


class ProductRepository(ABC):
    """Interface for product data access.

    The concrete implementation talks to a vector database for semantic search.
    """

    @abstractmethod
    def search(self, query: str) -> list[dict[str, object]]: ...

    @abstractmethod
    def get_all(self) -> list[dict[str, object]]: ...
