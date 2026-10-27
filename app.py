import os
import io
import tempfile
import streamlit as st
from PIL import Image
from document_processor import DocumentProcessor
from vector_store import VectorStore
from rag import RAG, PROVIDER_CONFIGS

st.set_page_config(
    page_title="DocuMind AI — Neural Document Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    /* Global style refinements */
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.8rem 2rem;
        border-radius: 1rem;
        color: #ffffff;
        margin-bottom: 1.8rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .main-header h1 {
        color: #ffffff !important;
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1.05rem;
        margin: 0;
    }
    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.8rem;
    }
    .tech-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.12);
        color: #e2e8f0;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 500;
        letter-spacing: 0.02em;
    }
    .card-box {
        padding: 1.25rem;
        border-radius: 0.75rem;
        background: #1e293b;
        color: #f8fafc !important;
        border: 1px solid #334155;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15);
    }
    .doc-pill {
        padding: 0.85rem 1rem;
        border-radius: 0.6rem;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
        border: 1px solid #334155 !important;
        border-left: 4px solid #3b82f6 !important;
        margin-bottom: 0.75rem;
        color: #f1f5f9 !important;
    }
    .doc-pill strong {
        color: #f8fafc !important;
    }
    .chat-bubble-user {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
        color: #f1f5f9 !important;
        border-radius: 0.85rem 0.85rem 0.2rem 0.85rem;
        padding: 1.1rem 1.35rem;
        margin: 0.9rem 0;
        border: 1px solid #334155 !important;
        border-left: 5px solid #3b82f6 !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
    }
    .chat-bubble-user .chat-title {
        color: #60a5fa !important;
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 0.45rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .chat-bubble-user .chat-text {
        color: #f8fafc !important;
        font-size: 1rem;
        line-height: 1.5;
        font-weight: 400;
        white-space: pre-wrap;
    }
    .chat-bubble-ai {
        background: linear-gradient(135deg, #062b1d 0%, #021a10 100%) !important;
        color: #ecfdf5 !important;
        border-radius: 0.85rem 0.85rem 0.85rem 0.2rem;
        padding: 1.1rem 1.35rem;
        margin: 0.9rem 0 1rem 0;
        border: 1px solid #065f46 !important;
        border-left: 5px solid #10b981 !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
    }
    .chat-bubble-ai .chat-title {
        color: #34d399 !important;
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 0.45rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .chat-bubble-ai .chat-text {
        color: #f0fdf4 !important;
        font-size: 1rem;
        line-height: 1.6;
        font-weight: 400;
        white-space: pre-wrap;
    }
    .chat-bubble-error {
        background: linear-gradient(135deg, #3d1414 0%, #200808 100%) !important;
        color: #fee2e2 !important;
        border-radius: 0.85rem 0.85rem 0.85rem 0.2rem;
        padding: 1.1rem 1.35rem;
        margin: 0.9rem 0 1rem 0;
        border: 1px solid #991b1b !important;
        border-left: 5px solid #ef4444 !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
    }
    .chat-bubble-error .chat-title {
        color: #f87171 !important;
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 0.45rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .chat-bubble-error .chat-text {
        color: #fecaca !important;
        font-size: 1rem;
        line-height: 1.6;
        font-weight: 400;
        white-space: pre-wrap;
    }
    .info-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
        border: 1px solid #334155 !important;
        border-radius: 0.75rem;
        padding: 1.2rem;
        margin-top: 1rem;
        color: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "vector_store" not in st.session_state:
    st.session_state.vector_store = VectorStore()
    
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []
    
if "raw_docs" not in st.session_state:
    st.session_state.raw_docs = {}
    
if "processor" not in st.session_state:
    st.session_state.processor = DocumentProcessor()
    
if "rag" not in st.session_state:
    st.session_state.rag = RAG(st.session_state.vector_store)
    
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def process_document(uploaded_file):
    """Process an uploaded document (PDF or image)."""
    file_name = getattr(uploaded_file, "name", "document.pdf")
    ext = os.path.splitext(file_name)[1].lower() if "." in file_name else ".pdf"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        raw_bytes = uploaded_file.getvalue()
        tmp_file.write(raw_bytes)
        tmp_path = tmp_file.name
    
    try:
        chunks = st.session_state.processor.process_document(tmp_path)
        st.session_state.vector_store.add_documents(chunks)
        
        # Save raw document bytes for source verification preview
        if "raw_docs" not in st.session_state:
            st.session_state.raw_docs = {}
        st.session_state.raw_docs[file_name] = raw_bytes
        
        # Calculate OCR statistics
        ocr_count = sum(1 for c in chunks if getattr(c, "metadata", {}).get("ocr_applied", False))
        
        if file_name not in [f["name"] for f in st.session_state.uploaded_files]:
            st.session_state.uploaded_files.append({
                "name": file_name,
                "size": getattr(uploaded_file, "size", len(raw_bytes)),
                "chunks": len(chunks),
                "ocr_chunks": ocr_count
            })
    except Exception as e:
        st.error(f"Error processing document: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

def clear_documents():
    """Clear all uploaded documents and reset the vector store and viewer cache."""
    st.session_state.vector_store = VectorStore()
    st.session_state.uploaded_files = []
    st.session_state.raw_docs = {}
    st.session_state.rag = RAG(st.session_state.vector_store)

# Hero Header
st.markdown("""
<div class="main-header">
    <h1>🧠 DocuMind AI</h1>
    <p>Enterprise-grade Retrieval-Augmented Generation (RAG) system with OCR fallback & original source inspection.</p>
    <div class="badge-container">
        <span class="tech-badge">⚡ FAISS Indexing</span>
        <span class="tech-badge">🧬 Sentence Transformers</span>
        <span class="tech-badge">🔍 OCR Fallback</span>
        <span class="tech-badge">🤖 Gemini / Groq / OpenAI</span>
        <span class="tech-badge">📖 Original Document Viewer</span>
        <span class="tech-badge">🔒 In-Memory Privacy</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🔑 AI Provider & Key")
    provider_names = list(PROVIDER_CONFIGS.keys())
    selected_provider = st.selectbox(
        "Choose AI Provider",
        provider_names,
        index=0,
        help="Select a free provider like Google Gemini or Groq to use DocuMind without paying"
    )
    
    cfg = PROVIDER_CONFIGS[selected_provider]
    
    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.7); padding: 0.7rem 0.9rem; border-radius: 0.6rem; border: 1px solid rgba(148, 163, 184, 0.2); font-size: 0.83rem; margin-bottom: 0.75rem;">
        <span style="color: #cbd5e1;">{cfg['help_text']}</span><br>
        <a href="{cfg['doc_url']}" target="_blank" style="color: #38bdf8; text-decoration: none; font-weight: 600; display: inline-block; margin-top: 0.35rem;">🔗 Get Free Key Here ↗</a>
    </div>
    """, unsafe_allow_html=True)
    
    env_key = os.getenv(cfg.get("env_var", ""), "")
    if not env_key and selected_provider == "OpenAI":
        env_key = os.getenv("OPENAI_API_KEY", "")
    if env_key and env_key.strip().startswith("your_"):
        env_key = ""
        
    api_key_input = st.text_input(
        f"{cfg['name']} API Key",
        value=env_key,
        type="password",
        placeholder="Paste your key here...",
        help=f"Provide your {cfg['name']} API Key"
    )
    if api_key_input:
        if api_key_input.strip().startswith("your_"):
            st.warning("Please replace the placeholder with your actual API key.")
        else:
            current_rag = st.session_state.rag
            if current_rag.provider != selected_provider or getattr(st.session_state, "_current_api_key", None) != api_key_input or not current_rag.model:
                success = current_rag.configure_llm(selected_provider, api_key_input)
                st.session_state._current_api_key = api_key_input
                st.session_state._current_provider = selected_provider
                os.environ[cfg.get("env_var", "OPENAI_API_KEY")] = api_key_input
                if success:
                    st.success(f"{cfg['name']} configured!")
                else:
                    st.error("Could not initialize model with this key.")
    elif st.session_state.rag.provider != selected_provider:
        st.session_state.rag.provider = selected_provider
        st.session_state.rag.model = None
    
    st.divider()
    st.header("📂 Ingest Documents")
    uploaded_file = st.file_uploader(
        "Upload PDF or Image Document",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        help="Select any text PDF, scanned document, or document image to index"
    )
    
    if uploaded_file is not None:
        if st.button("🚀 Process & Embed", type="primary", use_container_width=True):
            with st.spinner("Analyzing document, extracting text (with OCR fallback), and indexing vectors..."):
                process_document(uploaded_file)
                st.success(f"Indexed {uploaded_file.name} successfully!")
    
    st.divider()
    st.header("⚙️ Indexing Parameters")
    with st.expander("Chunking Settings", expanded=False):
        chunk_size = st.slider("Chunk Size (characters)", min_value=100, max_value=2000, value=1000, step=100, help="Target size for text segmentation")
        chunk_overlap = st.slider("Chunk Overlap (characters)", min_value=0, max_value=500, value=200, step=50, help="Overlap ensures contextual continuity between chunks")
        
        if chunk_size != st.session_state.processor.chunk_size or chunk_overlap != st.session_state.processor.chunk_overlap:
            st.session_state.processor = DocumentProcessor(chunk_size, chunk_overlap)
    
    if st.button("🗑️ Reset Knowledge Base", type="secondary", use_container_width=True):
        clear_documents()
        st.info("Knowledge base and documents reset.")
    
    st.divider()
    st.header("📑 Active Documents")
    if st.session_state.uploaded_files:
        for doc in st.session_state.uploaded_files:
            ocr_text = f" | OCR: <b>{doc.get('ocr_chunks', 0)} chunks</b>" if doc.get('ocr_chunks', 0) > 0 else ""
            st.markdown(f"""
            <div class="doc-pill">
                <strong>📄 {doc['name']}</strong><br>
                <small style="color: #94a3b8;">Chunks: <b>{doc['chunks']}</b> | Size: <b>{doc['size']/1024:.1f} KB</b>{ocr_text}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No documents loaded into active memory.")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Query Knowledge Base")
    question = st.text_input("Ask a question about your documents:", placeholder="e.g., What are the key points in this document?", label_visibility="collapsed")
    
    if st.button("Send Query", type="primary"):
        if not st.session_state.uploaded_files:
            st.warning("⚠️ Please upload and process at least one document first.")
        elif not question.strip():
            st.warning("⚠️ Please enter a question.")
        else:
            with st.spinner("Retrieving relevant passages and synthesizing verified answer..."):
                answer = st.session_state.rag.generate_answer(question)
                last_docs = getattr(st.session_state.rag, "last_retrieved_docs", [])
                sources = []
                for doc in last_docs:
                    m = getattr(doc, "metadata", {}) or {}
                    sources.append({
                        "source": m.get("source", "Document"),
                        "page": m.get("page", 1),
                        "extraction_method": m.get("extraction_method", "native"),
                        "distance": m.get("distance", None),
                        "content": getattr(doc, "page_content", "")
                    })
                st.session_state.chat_history.append({"question": question, "answer": answer, "sources": sources})
    
    # Display conversation history
    if st.session_state.chat_history:
        st.subheader("💭 Conversation History")
        for chat in reversed(st.session_state.chat_history):
            answer_text = chat['answer']
            is_error = answer_text.startswith("⚠️") or answer_text.startswith("Error")
            bubble_class = "chat-bubble-error" if is_error else "chat-bubble-ai"
            title_icon = "⚠️" if is_error else "🤖"
            title_text = "System Notice" if is_error else "DocuMind Assistant"
            
            st.markdown(f"""
            <div class="chat-bubble-user">
                <div class="chat-title">👤 Query</div>
                <div class="chat-text">{chat['question']}</div>
            </div>
            <div class="{bubble_class}">
                <div class="chat-title">{title_icon} {title_text}</div>
                <div class="chat-text">{answer_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Retrieved document excerpts inspector
            if chat.get("sources"):
                num_passages = len(chat["sources"])
                with st.expander(f"📄 View Retrieved Document Excerpts ({num_passages} passage{'s' if num_passages != 1 else ''})", expanded=False):
                    for idx, s in enumerate(chat["sources"]):
                        source_doc = s.get("source", "Document")
                        page_num = s.get("page", 1)
                        method = s.get("extraction_method", "native")
                        method_badge = "🔍 OCR Enhanced" if method == "ocr" else "⚡ Native Text"
                        dist = s.get("distance", None)
                        score_label = f" | L2 Distance: {dist:.3f}" if dist is not None else ""
                        
                        st.markdown(f"""
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(148, 163, 184, 0.2); border-left: 3px solid #38bdf8; border-radius: 0.5rem; padding: 0.8rem 1rem; margin-bottom: 0.75rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                                <span style="font-weight: 600; color: #93c5fa; font-size: 0.88rem;">Passage {idx+1} — 📄 {source_doc} (Page {page_num})</span>
                                <span style="font-size: 0.75rem; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 0.15rem 0.5rem; border-radius: 9999px;">{method_badge}{score_label}</span>
                            </div>
                            <div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.5; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;">{s.get('content', '')}</div>
                        </div>
                        """, unsafe_allow_html=True)

    # Document Inspection & Source Verification Section
    if st.session_state.uploaded_files and getattr(st.session_state, "raw_docs", None):
        st.divider()
        st.subheader("📖 Document Inspection & Source Verification")
        st.caption("Verify citations and inspect the original document pages directly.")
        
        doc_names = [f["name"] for f in st.session_state.uploaded_files]
        inspect_doc = st.selectbox("Select document to inspect:", doc_names, key="viewer_doc_select")
        
        if inspect_doc in st.session_state.raw_docs:
            raw_bytes = st.session_state.raw_docs[inspect_doc]
            ext = os.path.splitext(inspect_doc)[1].lower()
            
            if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                try:
                    img = Image.open(io.BytesIO(raw_bytes))
                    st.image(img, caption=f"Original File: {inspect_doc}", use_container_width=True)
                except Exception as e:
                    st.error(f"Error rendering image: {str(e)}")
            else:
                try:
                    import pypdfium2 as pdfium
                    pdf = pdfium.PdfDocument(raw_bytes)
                    total_p = len(pdf)
                    
                    if total_p > 1:
                        page_num = st.slider("Select page to view:", min_value=1, max_value=total_p, value=1)
                    else:
                        page_num = 1
                        
                    page_img = pdf[page_num - 1].render(scale=1.8).to_pil()
                    st.image(page_img, caption=f"{inspect_doc} — Page {page_num} of {total_p}", use_container_width=True)
                except Exception as e:
                    st.caption(f"Original preview unavailable ({str(e)}). Text content has been indexed.")

with col2:
    st.subheader("📊 Session Analytics")
    col_stats1, col_stats2 = st.columns(2)
    with col_stats1:
        total_docs = len(st.session_state.uploaded_files)
        st.metric("Documents", total_docs)
    with col_stats2:
        total_chunks = sum(doc["chunks"] for doc in st.session_state.uploaded_files) if st.session_state.uploaded_files else 0
        st.metric("Total Chunks", total_chunks)
    
    st.subheader("🔍 Architecture Pipeline")
    with st.expander("How RAG Operates", expanded=True):
        st.markdown("""
        1. **Multi-Engine Ingestion & OCR**: PDFs are processed via high-fidelity PDFium with automatic OCR fallback for scanned pages.
        2. **Dense Vector Embeddings**: Each segment is mapped to high-dimensional space via `all-MiniLM-L6-v2`.
        3. **FAISS Distance Ranking**: Sub-millisecond similarity index ranks the most pertinent passages.
        4. **Grounded Synthesis**: LLM synthesizes verified responses exclusively from retrieved evidence.
        5. **Original Source Verification**: Interactive document inspection verifies citations against the original document.
        """)

    st.markdown("""
    <div class="info-card">
        <h4 style="margin: 0 0 0.5rem 0; color: #f8fafc;">🔒 Privacy & Isolation</h4>
        <p style="margin: 0; font-size: 0.88rem; color: #94a3b8; line-height: 1.4;">
            All indexed vector representations remain strictly within local memory for this session. Raw PDF files are deleted from temporary disk immediately after parsing.
        </p>
    </div>
    """, unsafe_allow_html=True)