from app.product.catalog import load_products, products_by_id

EXPECTED_PRODUCT_COUNT = 20


class TestCatalog:
    def test_load_products_returns_full_catalog(self) -> None:
        assert len(load_products()) == EXPECTED_PRODUCT_COUNT

    def test_every_product_has_required_fields(self) -> None:
        required = {"id", "name", "category", "brand", "price", "stock", "specs", "description"}
        for product in load_products():
            assert required <= product.keys()

    def test_products_by_id_indexes_catalog(self) -> None:
        by_id = products_by_id()
        assert by_id["probook-15"]["name"] == "ProBook 15"
        assert len(by_id) == EXPECTED_PRODUCT_COUNT
