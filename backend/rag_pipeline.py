# rag_pipeline.py
import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)


def build_rag_pipeline(pdf_path):
    """
    Build a Retrieval-Augmented Generation (RAG) pipeline for a PDF document.
    """
    documents = PyMuPDFLoader(pdf_path).load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
    )

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",
        api_key=api_key,
    )

    retriever = vector_store.as_retriever(
        search_kwargs={"k": 3}
    )

    prompt = ChatPromptTemplate.from_template(
        """
        Answer the question using only the provided context.

        Context:
        {context}

        Question:
        {question}
        """
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain