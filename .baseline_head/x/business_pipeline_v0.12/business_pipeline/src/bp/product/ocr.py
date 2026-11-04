"""Reading a page with a vision model, when no local OCR can (product layer, optional).

The OCR chain has three engines and uses the cheapest one that can do the job:

1. **the PDF's own text layer** (``pypdf``, offline, exact) — always tried first;
2. **a local Tesseract** (offline, free, no key) — used when there is no text layer;
3. **a vision model** over an OpenAI-compatible ``chat/completions`` endpoint — this
   module — used when neither of the first two can read the page.

The model lane is **optional and fail-closed**, exactly like ``prose.py``: it is
available only when a gateway key **and** a model id are configured, so a fresh
install, a test run and an offline machine never open a socket.  Nothing here
guesses a model name: which vision model the gateway serves is the owner's
statement (``BP_OCR_MODEL``), never this module's assumption.

The transcription prompt is deliberately literal — transcribe, never summarise,
translate, correct or add — because the text becomes the student's brief, rubric
or evidence, and a model that "improves" a figure would change what the document
says.  The text is returned as **unverified**, like every other extracted text.
"""

import base64
import json
import os
import urllib.error
import urllib.request

#: The gateway the prose lane already uses; a different one may be named.
ENDPOINT = (os.environ.get("BP_OCR_URL") or os.environ.get("BP_PROSE_URL")
            or "https://opencode.ai/inference/go/openai/v1/chat/completions")

#: Where the owner names the vision model, most specific first.  No default: a model
#: id this module invented could be one the gateway does not serve.
MODEL_VARS = ("BP_OCR_MODEL", "BP_VISION_MODEL")

#: Two keys are accepted: the gateway the prose lane uses, or one kept for OCR alone.
KEY_VARS = ("BP_OPENGO_API_KEY", "BP_OCR_KEY")

PROMPT = (
    "Transcribe every character of this document page exactly as printed, in reading order. "
    "Keep the line breaks. Render a table as tab-separated rows. "
    "Do not summarise, translate, correct, explain or add anything that is not in the image. "
    "If the page carries no text, output nothing at all.")

#: A page image larger than this is refused rather than silently downscaled.
MAX_IMAGE_BYTES = 8_000_000

#: Fewer characters than this is not a page of text.
MIN_CHARS = 5


class OcrError(ValueError):
    """The page could not be read, and the message says why."""


def model_id():
    """The configured vision model id, or an empty string when none is named."""
    for name in MODEL_VARS:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return ""


def key():
    for name in KEY_VARS:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return ""


def available():
    """True only when both a key and a model id are configured."""
    return bool(key() and model_id())


def describe():
    """What would read a page right now, in words a record can carry."""
    if available():
        return {"engine": "vision_model", "model": model_id()}
    return {"engine": "none", "model": ""}


def _data_url(image_bytes, mime):
    return "data:%s;base64,%s" % (mime, base64.b64encode(image_bytes).decode("ascii"))


def read(image_bytes, mime="image/png", timeout=120):
    """One page of text from one image.  Raises :class:`OcrError` naming why not.

    An empty answer is an error, never an empty success: a page that produced no
    text must reach the student as "nothing was read", not as a blank document.
    """
    if not key():
        raise OcrError("no key is configured for the OCR model: set BP_OPENGO_API_KEY or BP_OCR_KEY")
    if not model_id():
        raise OcrError("no vision model is named for OCR: set BP_OCR_MODEL")
    if not image_bytes:
        raise OcrError("the page image is empty")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise OcrError("the page image is larger than the %d-byte limit; split the document"
                       % MAX_IMAGE_BYTES)
    payload = {"model": model_id(), "temperature": 0, "max_tokens": 4000,
               "messages": [{"role": "user", "content": [
                   {"type": "text", "text": PROMPT},
                   {"type": "image_url", "image_url": {"url": _data_url(image_bytes, mime)}}]}]}
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json",
                 "User-Agent": "smart-business-writer/1.0", "x-opencode-session": "bp-ocr"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise OcrError("the OCR model answered HTTP %s" % error.code)
    except Exception as error:
        raise OcrError("the OCR model could not be reached: " + str(error)[:160])
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise OcrError("the OCR model returned an unreadable response")
    if isinstance(content, list):
        content = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    text = str(content or "").strip()
    if len(text) < MIN_CHARS:
        raise OcrError("the OCR model read no text from this page")
    return text
