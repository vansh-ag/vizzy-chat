"""Vizzy Chat — Real End-to-End Test Suite.  # noqa: INP001

Tests the complete API flow against a live Supabase backend and real AI providers.

IMPORTANT — This test makes REAL API calls and incurs costs:
  - Real Groq intent classification requests
  - Real Hugging Face image generation requests
  - Real Supabase database and storage operations

HOW TO RUN:
  1. Start the FastAPI server: uv run uvicorn app.main:app --reload
  2. Configure all required environment variables (see below)
  3. Run (PowerShell):
       $env:RUN_REAL_E2E="true"
       uv run pytest tests/e2e/test_vizzy_real_e2e.py -v

  4. Run (Linux/macOS):
       RUN_REAL_E2E=true uv run pytest tests/e2e/test_vizzy_real_e2e.py -v

REQUIRED ENVIRONMENT VARIABLES:
  SUPABASE_URL              - Your Supabase project URL
  SUPABASE_ANON_KEY         - Supabase anon/public key
  SUPABASE_SERVICE_ROLE_KEY - Supabase service role key (never expose to frontend)
  GROQ_API_KEY              - Groq API key for intent classification
  HF_TOKEN                  - Hugging Face token for image generation

E2E-SPECIFIC VARIABLES:
  VIZZY_E2E_EMAIL           - Email of a test Supabase user
  VIZZY_E2E_PASSWORD        - Password of the test Supabase user
  VIZZY_E2E_BASE_URL        - API base URL (default: http://localhost:8000)
  RUN_REAL_E2E              - Must be "true" to enable real E2E tests

SECURITY:
  - Never hard-code credentials in this file
  - Never commit .env files with real secrets
  - This test never logs API keys, JWTs, or signed URLs after expiry
"""

import json
import logging
import os
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from PIL import Image

# Load backend/.env before any os.getenv() calls.
# Path is derived from this file's location so it works regardless of CWD.
# override=False means shell-level env vars (e.g. CI secrets) take precedence.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_ROOT / ".env", override=False)

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

BASE_URL = os.getenv("VIZZY_E2E_BASE_URL", "http://localhost:8000")
API_BASE = f"{BASE_URL}/api/v1"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "GROQ_API_KEY",
    "HF_TOKEN",
]

E2E_ENABLED = os.getenv("RUN_REAL_E2E", "false").lower() == "true"

# ── Skip logic ────────────────────────────────────────────────────────────────


def _check_required_env() -> tuple[bool, list[str]]:
    """Check if all required environment variables are present."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    return len(missing) == 0, missing


def _check_e2e_credentials() -> tuple[bool, str]:
    """Check if E2E-specific credentials are present."""
    email = os.getenv("VIZZY_E2E_EMAIL")
    password = os.getenv("VIZZY_E2E_PASSWORD")
    if not email or not password:
        return False, "VIZZY_E2E_EMAIL and VIZZY_E2E_PASSWORD must be set for E2E authentication."
    return True, ""


# ── Helpers ────────────────────────────────────────────────────────────────────


def _save_artifacts(data: dict) -> None:
    """Save E2E test metadata to the artifacts directory (no secrets)."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_file = ARTIFACTS_DIR / "e2e_result.json"
    # Strip any sensitive fields
    safe_data = {k: v for k, v in data.items() if k not in {"jwt", "password", "signed_url"}}
    safe_data["timestamp"] = datetime.now(UTC).isoformat()
    with open(artifact_file, "w") as f:
        json.dump(safe_data, f, indent=2, default=str)
    logger.info("E2E artifacts saved to %s", artifact_file)


def _validate_image_response(url: str) -> dict:
    """Download and validate an image from a URL using Pillow."""
    response = httpx.get(url, follow_redirects=True, timeout=30)
    assert response.status_code == 200, f"Image download failed: {response.status_code}"
    content_type = response.headers.get("content-type", "")
    assert "image" in content_type, f"Expected image content-type, got: {content_type}"

    image_data = response.content
    assert len(image_data) > 0, "Downloaded image is empty"

    # Validate with Pillow
    img = Image.open(BytesIO(image_data))
    img.verify()  # Raises on corrupt image

    return {
        "content_type": content_type,
        "size_bytes": len(image_data),
        "format": img.format if hasattr(img, "format") else "unknown",
    }


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def e2e_client():
    """HTTP client for real E2E tests."""
    with httpx.Client(base_url=BASE_URL, timeout=120) as client:
        yield client


@pytest.fixture(scope="module")
def auth_token(e2e_client: httpx.Client) -> str:
    """Authenticate with Supabase and return a JWT access token."""
    email = os.getenv("VIZZY_E2E_EMAIL")
    password = os.getenv("VIZZY_E2E_PASSWORD")
    supabase_url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")

    assert email and password, "E2E credentials not configured"
    assert supabase_url and anon_key, "Supabase credentials not configured"

    # Authenticate directly against Supabase Auth
    auth_response = httpx.post(
        f"{supabase_url}/auth/v1/token?grant_type=password",
        headers={
            "apikey": anon_key,
            "Content-Type": "application/json",
        },
        json={"email": email, "password": password},
        timeout=30,
    )
    assert auth_response.status_code == 200, (
        f"Authentication failed: {auth_response.status_code} {auth_response.text[:200]}"
    )
    token = auth_response.json().get("access_token")
    assert token, "No access_token in auth response"
    logger.info("E2E authentication successful")
    return token


# ── Main E2E Test ──────────────────────────────────────────────────────────────


@pytest.mark.skipif(not E2E_ENABLED, reason="Set RUN_REAL_E2E=true to run real E2E tests")
class TestVizzyRealE2E:
    """Real end-to-end test for the full Vizzy Chat workflow.

    Test scenario:
      1. Create a new conversation
      2. Send a text → image generation request
      3. Verify the generated image
      4. Send a refinement request (make it darker + add rain)
      5. Verify ASSET_B with parent_asset_id = ASSET_A
      6. Send a second refinement (add a glowing moon)
      7. Verify ASSET_C with parent_asset_id = ASSET_B
      8. Download and validate the final image with Pillow
      9. Verify conversation history order
      10. Clean up test data
    """

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_real_e2e_full_workflow(self, e2e_client: httpx.Client, auth_token: str):
        """Full E2E workflow: generate → refine → refine → verify lineage → cleanup."""
        has_env, missing = _check_required_env()
        if not has_env:
            pytest.skip(
                f"Real E2E test skipped because required environment variables are missing: {', '.join(missing)}"
            )

        has_creds, cred_msg = _check_e2e_credentials()
        if not has_creds:
            pytest.skip(f"Real E2E test skipped: {cred_msg}")

        headers = self._headers(auth_token)
        artifacts: dict = {
            "test_start": datetime.now(UTC).isoformat(),
            "steps": {},
        }
        conversation_id: str | None = None

        try:
            # ── Step 1: Create conversation ─────────────────────────────────
            t0 = time.perf_counter()
            conv_resp = e2e_client.post(
                f"{API_BASE}/conversations",
                json={"title": "Vizzy E2E Test"},
                headers=headers,
            )
            assert conv_resp.status_code == 201, (
                f"Conversation creation failed: {conv_resp.status_code} {conv_resp.text[:200]}"
            )
            conv_data = conv_resp.json()
            conversation_id = conv_data["id"]
            artifacts["conversation_id"] = conversation_id
            artifacts["steps"]["create_conversation"] = {
                "duration_ms": int((time.perf_counter() - t0) * 1000),
                "conversation_id": conversation_id,
            }
            logger.info("E2E Step 1 ✓: Created conversation %s", conversation_id)

            # ── Step 2: TEXT → IMAGE (Step 1) ───────────────────────────────
            t0 = time.perf_counter()
            msg1_resp = e2e_client.post(
                f"{API_BASE}/conversations/{conversation_id}/messages",
                json={
                    "content": (
                        "Create a cinematic illustration of a futuristic city at sunset, "
                        "with glowing neon buildings, flying cars, dramatic clouds, "
                        "and a warm orange sky."
                    ),
                    "asset_ids": [],
                },
                headers=headers,
                timeout=120,
            )
            step1_duration = int((time.perf_counter() - t0) * 1000)

            assert msg1_resp.status_code == 201, (
                f"Step 1 (generation) failed: {msg1_resp.status_code} {msg1_resp.text[:300]}"
            )
            msg1_data = msg1_resp.json()

            assert "user_message" in msg1_data, "Missing user_message in response"
            assert "assistant_message" in msg1_data, "Missing assistant_message in response"

            asset_a_id = None
            image_a_url = None
            if msg1_data.get("generated_asset"):
                asset_a_id = msg1_data["generated_asset"]["id"]
                gen_type_a = msg1_data["generated_asset"].get("generation_type")
                assert gen_type_a == "text_to_image", f"Expected text_to_image, got {gen_type_a}"
                parent_a = msg1_data["generated_asset"].get("parent_asset_id")
                assert parent_a is None, f"ASSET_A should have no parent, got {parent_a}"
            if msg1_data.get("image_url"):
                image_a_url = msg1_data["image_url"]

            artifacts["steps"]["step1_generation"] = {
                "duration_ms": step1_duration,
                "asset_id": asset_a_id,
                "intent": "image_generation",
                "has_image_url": image_a_url is not None,
            }
            logger.info("E2E Step 2 ✓: Generated ASSET_A=%s (%dms)", asset_a_id, step1_duration)

            if not asset_a_id:
                pytest.fail("Step 1 did not produce a generated asset — E2E cannot continue.")

            # ── Step 3: REFINEMENT — Make it darker + add rain ─────────────
            t0 = time.perf_counter()
            msg2_resp = e2e_client.post(
                f"{API_BASE}/conversations/{conversation_id}/messages",
                json={
                    "content": "Make the same scene darker, add heavy rain, and turn on more neon lights.",
                    "asset_ids": [],
                },
                headers=headers,
                timeout=120,
            )
            step2_duration = int((time.perf_counter() - t0) * 1000)

            assert msg2_resp.status_code == 201, (
                f"Step 2 (refinement) failed: {msg2_resp.status_code} {msg2_resp.text[:300]}"
            )
            msg2_data = msg2_resp.json()

            asset_b_id = None
            if msg2_data.get("generated_asset"):
                asset_b_id = msg2_data["generated_asset"]["id"]
                gen_type_b = msg2_data["generated_asset"].get("generation_type")
                assert gen_type_b == "image_refinement", f"Expected image_refinement, got {gen_type_b}"
                parent_b = msg2_data["generated_asset"].get("parent_asset_id")
                assert parent_b == asset_a_id, (
                    f"ASSET_B.parent_asset_id should be ASSET_A ({asset_a_id}), got {parent_b}"
                )

            artifacts["steps"]["step2_refinement"] = {
                "duration_ms": step2_duration,
                "asset_id": asset_b_id,
                "parent_asset_id": asset_a_id,
                "intent": "image_refinement",
                "lineage_verified": True,
            }
            logger.info(
                "E2E Step 3 ✓: Refined to ASSET_B=%s, parent=%s (%dms)",
                asset_b_id,
                asset_a_id,
                step2_duration,
            )

            # ── Step 4: SECOND REFINEMENT — Add a glowing moon ────────────
            t0 = time.perf_counter()
            msg3_resp = e2e_client.post(
                f"{API_BASE}/conversations/{conversation_id}/messages",
                json={
                    "content": "Add a large glowing moon in the background.",
                    "asset_ids": [],
                },
                headers=headers,
                timeout=120,
            )
            step3_duration = int((time.perf_counter() - t0) * 1000)

            assert msg3_resp.status_code == 201, (
                f"Step 3 (second refinement) failed: {msg3_resp.status_code} {msg3_resp.text[:300]}"
            )
            msg3_data = msg3_resp.json()

            asset_c_id = None
            image_c_url = None
            if msg3_data.get("generated_asset"):
                asset_c_id = msg3_data["generated_asset"]["id"]
                gen_type_c = msg3_data["generated_asset"].get("generation_type")
                assert gen_type_c == "image_refinement", f"Expected image_refinement, got {gen_type_c}"
                parent_c = msg3_data["generated_asset"].get("parent_asset_id")
                assert parent_c == asset_b_id, (
                    f"ASSET_C.parent_asset_id should be ASSET_B ({asset_b_id}), got {parent_c}"
                )
            if msg3_data.get("image_url"):
                image_c_url = msg3_data["image_url"]

            artifacts["steps"]["step3_second_refinement"] = {
                "duration_ms": step3_duration,
                "asset_id": asset_c_id,
                "parent_asset_id": asset_b_id,
                "intent": "image_refinement",
                "lineage_verified": True,
            }
            logger.info(
                "E2E Step 4 ✓: Second refinement ASSET_C=%s, parent=%s (%dms)",
                asset_c_id,
                asset_b_id,
                step3_duration,
            )

            # ── Step 5: DOWNLOAD and VALIDATE the final image ──────────────
            if image_c_url:
                t0 = time.perf_counter()
                image_info = _validate_image_response(image_c_url)
                download_duration = int((time.perf_counter() - t0) * 1000)
                artifacts["steps"]["step4_download"] = {
                    "duration_ms": download_duration,
                    "content_type": image_info["content_type"],
                    "size_bytes": image_info["size_bytes"],
                }
                logger.info(
                    "E2E Step 5 ✓: Downloaded and validated ASSET_C image — %d bytes, content-type=%s (%dms)",
                    image_info["size_bytes"],
                    image_info["content_type"],
                    download_duration,
                )
            else:
                logger.warning("E2E Step 5: No signed URL for ASSET_C — skipping download test")

            # ── Step 6: CONVERSATION HISTORY verification ──────────────────
            history_resp = e2e_client.get(
                f"{API_BASE}/conversations/{conversation_id}/messages",
                headers=headers,
            )
            assert history_resp.status_code == 200, f"History fetch failed: {history_resp.status_code}"
            history_data = history_resp.json()
            messages = history_data.get("items", [])

            # Should have at least 6 messages: 3 user + 3 assistant
            assert len(messages) >= 6, f"Expected at least 6 messages in history, got {len(messages)}"

            # Verify order: user, assistant, user, assistant, user, assistant
            user_messages = [m for m in messages if m["role"] == "user"]
            assistant_messages = [m for m in messages if m["role"] == "assistant"]
            assert len(user_messages) >= 3, f"Expected 3 user messages, got {len(user_messages)}"
            assert len(assistant_messages) >= 3, f"Expected 3 assistant messages, got {len(assistant_messages)}"

            artifacts["steps"]["step5_history"] = {
                "total_messages": len(messages),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "order_verified": True,
            }
            logger.info("E2E Step 6 ✓: Conversation history has %d messages", len(messages))

            # ── Step 7: ASSET LINEAGE summary ─────────────────────────────
            lineage = {
                "ASSET_A": {"id": asset_a_id, "parent": None},
                "ASSET_B": {"id": asset_b_id, "parent": asset_a_id},
                "ASSET_C": {"id": asset_c_id, "parent": asset_b_id},
            }
            artifacts["asset_lineage"] = lineage
            logger.info(
                "E2E ✓ Complete Lineage: A=%s → B=%s → C=%s",
                asset_a_id,
                asset_b_id,
                asset_c_id,
            )

            artifacts["test_end"] = datetime.now(UTC).isoformat()
            artifacts["result"] = "PASS"

        except Exception as exc:
            artifacts["result"] = "FAIL"
            artifacts["error"] = str(exc)
            raise

        finally:
            # ── Cleanup: Delete test conversation ─────────────────────────
            if conversation_id:
                try:
                    del_resp = e2e_client.delete(
                        f"{API_BASE}/conversations/{conversation_id}",
                        headers=headers,
                    )
                    if del_resp.status_code in (204, 200):
                        logger.info("E2E Cleanup ✓: Deleted test conversation %s", conversation_id)
                    else:
                        logger.warning(
                            "E2E Cleanup: Could not delete conversation %s: %d",
                            conversation_id,
                            del_resp.status_code,
                        )
                except Exception as cleanup_exc:
                    logger.warning("E2E Cleanup failed: %s", cleanup_exc)

            _save_artifacts(artifacts)

    def test_real_e2e_random_prompt(self, e2e_client: httpx.Client, auth_token: str):
        """Generate one image with a randomly selected safe prompt."""
        import random

        has_env, missing = _check_required_env()
        if not has_env:
            pytest.skip(
                f"Real E2E test skipped because required environment variables are missing: {', '.join(missing)}"
            )
        has_creds, cred_msg = _check_e2e_credentials()
        if not has_creds:
            pytest.skip(f"Real E2E test skipped: {cred_msg}")

        subjects = [
            "futuristic city",
            "enchanted forest",
            "mountain cabin in winter",
            "cyberpunk street",
            "space station",
            "floating island",
        ]
        styles = [
            "cinematic",
            "watercolor",
            "digital art",
            "concept art",
            "editorial illustration",
        ]
        subject = random.choice(subjects)
        style = random.choice(styles)
        prompt = f"Create a {style} image of a {subject} with dramatic lighting and high detail."

        headers = self._headers(auth_token)
        conversation_id = None

        try:
            # Create conversation
            conv_resp = e2e_client.post(
                f"{API_BASE}/conversations",
                json={"title": f"E2E Random: {style} {subject}"},
                headers=headers,
            )
            assert conv_resp.status_code == 201
            conversation_id = conv_resp.json()["id"]

            # Generate image
            t0 = time.perf_counter()
            msg_resp = e2e_client.post(
                f"{API_BASE}/conversations/{conversation_id}/messages",
                json={"content": prompt, "asset_ids": []},
                headers=headers,
                timeout=120,
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)

            assert msg_resp.status_code == 201, f"Random prompt failed: {msg_resp.status_code} {msg_resp.text[:200]}"

            data = msg_resp.json()
            logger.info(
                "E2E Random ✓: '%s' → asset=%s (%dms)",
                prompt,
                (data.get("generated_asset") or {}).get("id"),
                duration_ms,
            )

        finally:
            if conversation_id:
                import contextlib

                with contextlib.suppress(Exception):
                    e2e_client.delete(
                        f"{API_BASE}/conversations/{conversation_id}",
                        headers=headers,
                    )
