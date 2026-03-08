from langchain.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer
import os




# Extracting Data from PDF
def load_pdf(data):
  loader = DirectoryLoader(data, glob="*.pdf", loader_cls=PyPDFLoader)
  documents = loader.load()
  return documents

# Creating Text Chunks
def text_split(extracted_data):
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
  text_chunks = text_splitter.split_documents(extracted_data)
  return text_chunks


# Download the embedding model
def download_hugging_face_embeddings():

    # Force offline mode
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"local_files_only": True}
    )

    return embeddings