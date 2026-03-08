from langchain.vectorstores import FAISS
from src.helper import load_pdf, text_split, download_hugging_face_embeddings

print("Loading PDF...")
extracted_data = load_pdf("data/")

print("Splitting text...")
text_chunks = text_split(extracted_data)

print("Loading embeddings model...")
embeddings = download_hugging_face_embeddings()

print("Creating FAISS index...")
docsearch = FAISS.from_texts(
    [t.page_content for t in text_chunks],
    embeddings
)

print("Saving FAISS index locally...")
docsearch.save_local("faiss_index")

print("✅ FAISS index created successfully!")