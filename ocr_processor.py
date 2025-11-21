"""
OCR Processor for Portfolio Crusher X2

Extracts portfolio positions from images using Anthropic's Claude Vision API.
Supports screenshots from brokers like Robinhood, Fidelity, Schwab, etc.
"""

import os
import base64
import logging
from typing import Dict, List, Optional, Any
from anthropic import Anthropic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security constraints
MAX_IMAGE_SIZE_MB = 10
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif"
]


def validate_image_input(image_data: bytes, mime_type: str) -> None:
    """
    Validate image data meets security requirements.

    Args:
        image_data: Raw image bytes
        mime_type: MIME type of the image

    Raises:
        ValueError: If validation fails

    Example:
        >>> with open("portfolio.png", "rb") as f:
        ...     data = f.read()
        >>> validate_image_input(data, "image/png")
    """
    if not image_data:
        raise ValueError("Image data is empty")

    if not isinstance(image_data, bytes):
        raise ValueError("Image data must be bytes")

    if len(image_data) > MAX_IMAGE_SIZE_BYTES:
        raise ValueError(
            f"Image size {len(image_data) / 1024 / 1024:.2f}MB exceeds "
            f"maximum allowed size of {MAX_IMAGE_SIZE_MB}MB"
        )

    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"MIME type '{mime_type}' not allowed. "
            f"Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    logger.info(f"Image validation passed: {len(image_data)} bytes, {mime_type}")


def extract_positions_from_image(
    image_data: bytes,
    mime_type: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract portfolio positions from an image using Claude Vision API.

    Args:
        image_data: Raw image bytes
        mime_type: MIME type of the image (e.g., "image/png", "image/jpeg")
        api_key: Optional Anthropic API key. If not provided, reads from
                ANTHROPIC_API_KEY environment variable.

    Returns:
        Dictionary containing:
        {
            "success": bool,
            "positions": [
                {
                    "ticker": str,
                    "quantity": float,
                    "current_value": float,
                    "cost_basis": float or None,
                    "confidence": str  # "high", "medium", "low"
                },
                ...
            ],
            "raw_text": str,  # Raw extracted text for debugging
            "metadata": {
                "broker": str or None,
                "account_type": str or None,
                "total_value": float or None
            },
            "error": str or None
        }

    Raises:
        ValueError: If image validation fails
        Exception: If API call fails

    Example:
        >>> with open("portfolio.png", "rb") as f:
        ...     image_bytes = f.read()
        >>> result = extract_positions_from_image(image_bytes, "image/png")
        >>> if result["success"]:
        ...     for pos in result["positions"]:
        ...         print(f"{pos['ticker']}: {pos['quantity']} shares")
    """
    try:
        # Validate input
        validate_image_input(image_data, mime_type)

        # Get API key
        if api_key is None:
            api_key = os.getenv('ANTHROPIC_API_KEY')

        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables. "
                "Please set it in your .env file or pass it explicitly."
            )

        # Initialize Anthropic client
        client = Anthropic(api_key=api_key)

        # Encode image to base64
        image_base64 = base64.standard_b64encode(image_data).decode('utf-8')

        # Construct prompt for position extraction
        extraction_prompt = """
You are analyzing a portfolio screenshot. Extract ALL visible stock/ETF positions.

For each position, extract:
1. Ticker symbol (e.g., AAPL, SPY, TSLA)
2. Quantity/shares held
3. Current market value in USD
4. Cost basis or purchase price (if visible)

Return ONLY valid JSON in this exact format:
{
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 10.5,
      "current_value": 1850.25,
      "cost_basis": 1500.00,
      "confidence": "high"
    }
  ],
  "metadata": {
    "broker": "Robinhood",
    "account_type": "Individual Brokerage",
    "total_value": 50000.00
  }
}

Rules:
- Use "confidence": "high" if ticker and numbers are clearly visible
- Use "confidence": "medium" if some uncertainty exists
- Use "confidence": "low" if guessing or unclear
- Set cost_basis to null if not visible
- Include fractional shares if visible
- Extract broker name and account type if visible
- Calculate total portfolio value if visible

Extract positions now:
"""

        logger.info("Sending image to Claude Vision API for OCR processing")

        # Call Claude Vision API
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": extraction_prompt
                        }
                    ],
                }
            ],
        )

        # Extract response text
        response_text = message.content[0].text
        logger.info(f"Received response from Claude API: {len(response_text)} characters")

        # Parse JSON response
        import json

        # Try to find JSON in the response
        # Sometimes the model includes extra text before/after JSON
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            logger.warning("No JSON found in response, returning raw text")
            return {
                "success": False,
                "positions": [],
                "raw_text": response_text,
                "metadata": {},
                "error": "No structured data found in image. Response: " + response_text[:200]
            }

        json_str = response_text[json_start:json_end]
        parsed_data = json.loads(json_str)

        # Validate parsed data structure
        if "positions" not in parsed_data:
            parsed_data["positions"] = []

        if "metadata" not in parsed_data:
            parsed_data["metadata"] = {}

        # Validate each position has required fields
        validated_positions = []
        for pos in parsed_data.get("positions", []):
            if not isinstance(pos, dict):
                continue

            # Required fields
            if "ticker" not in pos or "quantity" not in pos:
                logger.warning(f"Skipping position missing required fields: {pos}")
                continue

            # Ensure numeric fields
            try:
                validated_pos = {
                    "ticker": str(pos["ticker"]).upper().strip(),
                    "quantity": float(pos.get("quantity", 0)),
                    "current_value": float(pos.get("current_value", 0)),
                    "cost_basis": float(pos["cost_basis"]) if pos.get("cost_basis") else None,
                    "confidence": pos.get("confidence", "medium")
                }
                validated_positions.append(validated_pos)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error validating position {pos}: {e}")
                continue

        result = {
            "success": True,
            "positions": validated_positions,
            "raw_text": response_text,
            "metadata": parsed_data.get("metadata", {}),
            "error": None
        }

        logger.info(f"Successfully extracted {len(validated_positions)} positions")
        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {
            "success": False,
            "positions": [],
            "raw_text": "",
            "metadata": {},
            "error": str(e)
        }

    except Exception as e:
        logger.error(f"Error extracting positions from image: {e}", exc_info=True)
        return {
            "success": False,
            "positions": [],
            "raw_text": "",
            "metadata": {},
            "error": f"OCR processing failed: {str(e)}"
        }


def extract_positions_from_file(
    file_path: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract portfolio positions from an image file.

    Convenience wrapper around extract_positions_from_image that reads from a file.

    Args:
        file_path: Path to image file
        api_key: Optional Anthropic API key

    Returns:
        Same as extract_positions_from_image

    Example:
        >>> result = extract_positions_from_file("my_portfolio.png")
        >>> print(f"Found {len(result['positions'])} positions")
    """
    try:
        # Determine MIME type from file extension
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)

        if not mime_type:
            # Default to png if unknown
            file_ext = file_path.lower().split('.')[-1]
            mime_type_map = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'webp': 'image/webp',
                'gif': 'image/gif'
            }
            mime_type = mime_type_map.get(file_ext, 'image/png')

        logger.info(f"Reading image file: {file_path} (detected type: {mime_type})")

        # Read file
        with open(file_path, 'rb') as f:
            image_data = f.read()

        return extract_positions_from_image(image_data, mime_type, api_key)

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return {
            "success": False,
            "positions": [],
            "raw_text": "",
            "metadata": {},
            "error": f"File not found: {file_path}"
        }
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return {
            "success": False,
            "positions": [],
            "raw_text": "",
            "metadata": {},
            "error": f"Error reading file: {str(e)}"
        }


if __name__ == "__main__":
    # Example usage / testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr_processor.py <image_path>")
        print("\nExample:")
        print("  python ocr_processor.py portfolio_screenshot.png")
        sys.exit(1)

    image_path = sys.argv[1]
    print(f"\n🔍 Extracting positions from: {image_path}\n")

    result = extract_positions_from_file(image_path)

    if result["success"]:
        print(f"✅ Successfully extracted {len(result['positions'])} positions:\n")

        for i, pos in enumerate(result["positions"], 1):
            print(f"{i}. {pos['ticker']}")
            print(f"   Quantity: {pos['quantity']}")
            print(f"   Current Value: ${pos['current_value']:,.2f}")
            if pos['cost_basis']:
                print(f"   Cost Basis: ${pos['cost_basis']:,.2f}")
                gain_loss = pos['current_value'] - pos['cost_basis']
                gain_loss_pct = (gain_loss / pos['cost_basis']) * 100
                print(f"   Gain/Loss: ${gain_loss:,.2f} ({gain_loss_pct:+.2f}%)")
            print(f"   Confidence: {pos['confidence']}")
            print()

        if result["metadata"]:
            print("📊 Portfolio Metadata:")
            for key, value in result["metadata"].items():
                if value:
                    print(f"   {key}: {value}")
            print()
    else:
        print(f"❌ Error: {result['error']}\n")
        if result.get("raw_text"):
            print("Raw response:")
            print(result["raw_text"])
