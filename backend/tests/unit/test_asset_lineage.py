"""Unit tests for asset lineage — parent_asset_id relationships."""

from unittest.mock import MagicMock, patch

from app.db.repositories.asset import AssetRepository


def _make_asset(asset_id: str, user_id: str, parent_id: str | None = None) -> dict:
    return {
        "id": asset_id,
        "user_id": user_id,
        "conversation_id": "conv-1",
        "message_id": None,
        "type": "image",
        "storage_path": f"generated-images/user-1/conv-1/{asset_id}.png",
        "mime_type": "image/png",
        "prompt": "test prompt",
        "generation_type": "text_to_image",
        "parent_asset_id": parent_id,
        "created_at": "2026-01-01T00:00:00Z",
    }


class TestAssetLineage:
    """Tests for asset parent-child lineage through the repository."""

    @patch("app.db.repositories.asset.get_service_client")
    def test_create_generated_asset_with_parent(self, mock_get_client):
        """create_generated_asset should include parent_asset_id in the record."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Simulate the Supabase insert response
        parent_id = "parent-asset-id"
        expected_asset = _make_asset("child-id", "user-1", parent_id)
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [expected_asset]

        repo = AssetRepository()
        result = repo.create_generated_asset(
            user_id="user-1",
            conversation_id="conv-1",
            message_id=None,
            storage_path="generated-images/user-1/conv-1/child.png",
            mime_type="image/png",
            prompt="test",
            generation_type="image_refinement",
            parent_asset_id=parent_id,
        )

        assert result["parent_asset_id"] == parent_id
        # Verify the insert was called with parent_asset_id in the record
        insert_call = mock_client.table.return_value.insert.call_args[0][0]
        assert insert_call["parent_asset_id"] == parent_id
        assert insert_call["generation_type"] == "image_refinement"

    @patch("app.db.repositories.asset.get_service_client")
    def test_create_generated_asset_without_parent(self, mock_get_client):
        """create_generated_asset should have parent_asset_id=None for new generations."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        expected_asset = _make_asset("new-id", "user-1", None)
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [expected_asset]

        repo = AssetRepository()
        result = repo.create_generated_asset(
            user_id="user-1",
            conversation_id="conv-1",
            message_id=None,
            storage_path="generated-images/user-1/conv-1/new.png",
            mime_type="image/png",
            prompt="test",
            generation_type="text_to_image",
        )

        assert result["parent_asset_id"] is None
        insert_call = mock_client.table.return_value.insert.call_args[0][0]
        assert insert_call["parent_asset_id"] is None

    @patch("app.db.repositories.asset.get_service_client")
    def test_get_asset_children_returns_lineage(self, mock_get_client):
        """get_asset_children should return all child assets of a given parent."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        child_assets = [
            _make_asset("child-1", "user-1", "parent-id"),
            _make_asset("child-2", "user-1", "parent-id"),
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = child_assets

        repo = AssetRepository()
        children = repo.get_asset_children("parent-id", "user-1")

        assert len(children) == 2
        assert all(c["parent_asset_id"] == "parent-id" for c in children)

    @patch("app.db.repositories.asset.get_service_client")
    def test_create_asset_input_relationship(self, mock_get_client):
        """create_asset_input_relationship should insert into asset_inputs table."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        rel_record = {
            "id": "rel-id",
            "output_asset_id": "output-id",
            "input_asset_id": "input-id",
        }
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [rel_record]

        repo = AssetRepository()
        result = repo.create_asset_input_relationship(
            output_asset_id="output-id",
            input_asset_id="input-id",
        )

        assert result["output_asset_id"] == "output-id"
        assert result["input_asset_id"] == "input-id"

        # Verify correct table was used
        table_call = mock_client.table.call_args[0][0]
        assert table_call == "asset_inputs"


class TestAssetLineageChain:
    """Tests for multi-step lineage chains (A → B → C)."""

    def test_lineage_chain_structure(self):
        """Verify asset lineage chain representation is correct conceptually."""
        # Asset A: root (no parent)
        asset_a = _make_asset("a", "user-1", None)
        # Asset B: child of A
        asset_b = _make_asset("b", "user-1", "a")
        # Asset C: child of B
        asset_c = _make_asset("c", "user-1", "b")

        # Verify the chain
        assert asset_a["parent_asset_id"] is None
        assert asset_b["parent_asset_id"] == asset_a["id"]
        assert asset_c["parent_asset_id"] == asset_b["id"]

        # Traverse the chain
        chain = [asset_a, asset_b, asset_c]
        for i in range(1, len(chain)):
            assert chain[i]["parent_asset_id"] == chain[i - 1]["id"]
