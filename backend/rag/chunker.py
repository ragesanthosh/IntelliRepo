from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.config import get_settings


def chunk_documents(files: list[dict]) -> list[dict]:
    """Split file contents into chunks with metadata."""
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = []
    for file_data in files:
        file_path = file_data["path"]
        content = file_data["content"]
        text_chunks = splitter.split_text(content)

        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    "source": file_path,
                    "chunk_index": i,
                },
            })

    return chunks
