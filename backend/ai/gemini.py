import json
import re
import google.generativeai as genai
from utils.config import get_settings
from ai.prompts import REPOSITORY_ANALYSIS_PROMPT, CHAT_SYSTEM_PROMPT


def _configure_gemini():
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)


def _get_model():
    _configure_gemini()
    settings = get_settings()
    return genai.GenerativeModel(settings.gemini_model)


def _extract_json(text: str) -> dict:
    """Extract JSON from model response, handling markdown fences."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


def _prepare_file_samples(files: list[dict], max_files: int = 15) -> str:
    """Select representative files for analysis."""
    priority_extensions = [".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md"]
    sorted_files = sorted(
        files,
        key=lambda f: (
            0 if any(f["path"].endswith(e) for e in ["main.", "index.", "app.", "__init__"]) else 1,
            priority_extensions.index(f["extension"]) if f["extension"] in priority_extensions else 99,
            len(f["path"]),
        ),
    )

    samples = []
    total_chars = 0
    max_chars = 30000

    for f in sorted_files[:max_files]:
        if total_chars >= max_chars:
            break
        content = f["content"][:3000]
        sample = f"--- {f['path']} ---\n{content}\n"
        samples.append(sample)
        total_chars += len(sample)

    return "\n".join(samples)


def generate_repository_analysis(
    owner: str,
    repo_name: str,
    url: str,
    files: list[dict],
    folder_structure: str,
) -> dict:
    model = _get_model()
    file_samples = _prepare_file_samples(files)

    prompt = REPOSITORY_ANALYSIS_PROMPT.format(
        owner=owner,
        repo_name=repo_name,
        url=url,
        folder_structure=folder_structure,
        file_samples=file_samples,
    )

    response = model.generate_content(prompt)
    return _extract_json(response.text)


def generate_chat_response(
    question: str,
    summary: dict | str,
    context_chunks: list[dict],
    history: list[dict] | None = None,
) -> str:
    model = _get_model()

    if isinstance(summary, dict):
        summary_text = summary.get("project_summary", json.dumps(summary, indent=2))
    else:
        summary_text = str(summary)

    context_parts = []
    for chunk in context_chunks:
        source = chunk.get("source", "unknown")
        content = chunk.get("content", "")
        context_parts.append(f"[{source}]\n{content}")

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant code found."

    system_prompt = CHAT_SYSTEM_PROMPT.format(
        summary=summary_text,
        context=context,
    )

    messages = []
    if history:
        for msg in history[-6:]:
            role = "user" if msg.get("role") == "user" else "model"
            messages.append({"role": role, "parts": [msg.get("content", "")]})

    chat = model.start_chat(history=messages)
    full_prompt = f"{system_prompt}\n\nUser Question: {question}"
    response = chat.send_message(full_prompt)
    return response.text
