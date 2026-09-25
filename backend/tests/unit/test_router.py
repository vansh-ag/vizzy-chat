"""Tests for deterministic routing — Phase 4."""

from app.ai.intent.schemas import IntentType
from app.ai.router.task_router import route_intent


def test_route_intent_image_generation():
    """IMAGE_GENERATION should route to generate_image."""
    assert route_intent(IntentType.IMAGE_GENERATION) == "generate_image"


def test_route_intent_image_transformation():
    """IMAGE_TRANSFORMATION should route to transform_image."""
    assert route_intent(IntentType.IMAGE_TRANSFORMATION) == "transform_image"


def test_route_intent_image_refinement():
    """IMAGE_REFINEMENT should route to refine_image."""
    assert route_intent(IntentType.IMAGE_REFINEMENT) == "refine_image"


def test_route_intent_multi_image_transformation():
    """MULTI_IMAGE_TRANSFORMATION should route to transform_multiple_images."""
    assert route_intent(IntentType.MULTI_IMAGE_TRANSFORMATION) == "transform_multiple_images"


def test_route_intent_unsupported():
    """UNSUPPORTED should route to unsupported_request."""
    assert route_intent(IntentType.UNSUPPORTED) == "unsupported_request"
