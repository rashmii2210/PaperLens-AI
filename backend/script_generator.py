# script_generator.py
import re
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)


def safe_json_loads(text):
    """Strip invalid control characters before parsing JSON from LLM output."""
    text = text.strip()
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return json.loads(cleaned)


def build_vectorstore(pdf_path):
    print("Loading PDF...")
    loader = PyMuPDFLoader(pdf_path)
    docs = loader.load()
    print(f"Loaded {len(docs)} pages")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200
    )
    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")
    if not chunks:
        raise ValueError(
            "This PDF has no extractable text. "
            "It may be a scanned document or image-based PDF. "
            "Please upload a text-based PDF."
        )
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vectordb = Chroma.from_documents(chunks, embeddings)
    print("Vector store ready\n")
    return vectordb


def get_paper_overview(vectordb, llm):
    print("Extracting paper overview...")
    retriever = vectordb.as_retriever(search_kwargs={"k": 3})
    prompt = ChatPromptTemplate.from_template(
        """
    You are a research paper analyst.
    Based on the context below, extract:
    1. Paper title (if found, else make a suitable one)
    2. Main topic in 1 sentence
    3. Between 3 to 5 logical sections that best summarize this specific document.
       - For research papers: use Introduction, Methodology, Results, Discussion, Conclusion
       - For textbooks/notes: use Overview, Core Concepts, Key Topics, Applications, Summary
       - For reports: use Executive Summary, Findings, Analysis, Recommendations, Conclusion
       - Adapt based on what the document actually contains — don't force sections that don't exist
    4. 5 most important concepts/findings from the document

    Context:
    {context}

    Question: {question}

    Respond in this exact JSON format:
    {{
        "title": "...",
        "main_topic": "...",
        "sections": ["section1", "section2", "section3", "section4", "section5"],
        "key_concepts": ["concept1", "concept2", "concept3", "concept4", "concept5"]
    }}
    Only respond with JSON, nothing else.
    """
    )
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    result = chain.invoke(
        "What is this paper about? What are its main sections and key concepts?"
    )
    result = result.strip()
    if result.startswith("```"):
        result = result.split("```")[1]
        if result.startswith("json"):
            result = result[4:]
    overview = safe_json_loads(result)
    print(f"Paper: {overview['title']}\n")
    return overview


def generate_section_script(section_title, key_concepts, vectordb, llm, is_final=False, main_topic="", used_visual_hints=None):
    print(f"Writing script for: {section_title}")
    used_visual_hints = used_visual_hints or []
    retriever = vectordb.as_retriever(search_kwargs={"k": 2})
    prompt = ChatPromptTemplate.from_template(
        """
    You are a YouTube educator who explains research papers in an engaging way.
    Write a video script section for "{section_title}".
    
    Key concepts to cover: {key_concepts}
    
    Context from paper:
    {context}
    
    This section IS_FINAL = {is_final}

    Rules:
    - Speak directly to the viewer (use "you", "we", "let's")
    - Use simple language; explain any necessary jargon
    - Scale the script length based on section complexity:
    * Simple/short section: 30-40 words
    * Medium section: 50-70 words
    * Complex/detailed section: 80-100 words
    - Never exceed 100 words per section
    - Start each section with a hook or transition phrase
    - Do NOT end with phrases like "let's visualize", "let's explore", "in the next section", "we'll see", or "coming up"
    - The last sentence must be a complete thought, not a teaser
    - The visual_hint field must be a short, concrete, photographable noun phrase (2-4 words) suitable for a stock photo search
    - The visual_hint MUST relate to the paper's main_topic ({main_topic}) AND must visually represent THIS section's specific content, not the paper as a whole
    - Already used in earlier sections (DO NOT repeat these or close variations): {used_visual_hints}
    - Your visual_hint must be clearly different from every hint listed above — pick a different concrete subject, scene, or angle entirely
    - Good examples for a tech/AI paper: "computer code screen", "scientist analyzing data", "data center servers", "team whiteboard discussion", "robotic arm assembly", "graph chart presentation"
    - Bad examples: "conclusion", "summary", "learning", "understanding" — these are too generic and return random unrelated photos
    - Never use single abstract words like "growth", "future", "success" as the visual_hint
    - Do NOT mention visuals, diagrams, images, or animations inside the script text
    - The script must work as pure audio narration without relying on visual references

    IF IS_FINAL is True:
    - End with "Thanks for watching!" or a clear concluding call to action
    
    IF IS_FINAL is False:
    - End with a strong concluding sentence that summarizes what was just explained
    - NEVER use "Thanks for watching!", "Subscribe", "Like and subscribe", "Follow for more", or any call to action        
    Respond in this exact JSON format:
    {{
        "title": "{section_title}",
        "script": "...",
        "duration": "60 sec",
        "visual_hint": "...",
        "key_points": ["point1", "point2", "point3"]
    }}
    Only respond with JSON, nothing else.
    """
    )
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    chain = (
        {
            "context": retriever | format_docs,
            "section_title": lambda _: section_title,
            "key_concepts": lambda _: ", ".join(key_concepts),
            "is_final": lambda _: str(is_final),
            "main_topic": lambda _: main_topic,
            "used_visual_hints": lambda _: ", ".join(used_visual_hints) if used_visual_hints else "(none yet — this is the first section)",
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    result = chain.invoke(f"Explain the {section_title} section of this paper")
    result = result.strip()
    if result.startswith("```"):
        result = result.split("```")[1]
        if result.startswith("json"):
            result = result[4:]
    return safe_json_loads(result)

def generate_full_script(pdf_path):
    vectordb = build_vectorstore(pdf_path)
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY")
    )
    overview = get_paper_overview(vectordb, llm)
    print("Generating video script sections...\n")
    video_sections = []
    used_visual_hints = []  # NEW: track hints across sections

    total = len(overview["sections"])
    for idx, section in enumerate(overview["sections"]):
        is_final = (idx == total - 1)
        section_script = generate_section_script(
            section_title=section,
            key_concepts=overview["key_concepts"],
            vectordb=vectordb,
            llm=llm,
            is_final=is_final,
            main_topic=overview["main_topic"],
            used_visual_hints=used_visual_hints,  # NEW
        )
        video_sections.append(section_script)
        used_visual_hints.append(section_script["visual_hint"])  # NEW: record it

    full_script = {
        "paper_title": overview["title"],
        "main_topic": overview["main_topic"],
        "total_sections": len(video_sections),
        "estimated_duration": f"{len(video_sections) * 40} seconds (~{len(video_sections) * 40 // 60} min)",
        "sections": video_sections,
    }
    return full_script

if __name__ == "__main__":
    script = generate_full_script("paper.pdf")
    with open("video_script.json", "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    print("\n" + "=" * 60)
    print("VIDEO SCRIPT GENERATED!")
    print("=" * 60)
    print(f"Title    : {script['paper_title']}")
    print(f"Sections : {script['total_sections']}")
    print(f"Duration : {script['estimated_duration']}")
    print("\nFull script saved to: video_script.json")
    print("=" * 60)
    print("\nPREVIEW — First Section:")
    print("-" * 40)
    first = script["sections"][0]
    print(f"Title      : {first['title']}")
    print(f"Duration   : {first['duration']}")
    print(f"Visual     : {first['visual_hint']}")
    print(f"Script     : {first['script'][:200]}...")