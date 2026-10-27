from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="documind-ai",
    version="1.0.0",
    author="Sarthak Takle",
    author_email="112315165@cse.iiitp.ac.in",
    description="High-performance Retrieval-Augmented Generation (RAG) assistant for documents with FAISS and Streamlit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sarthak-takle/DocuMind_ai",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langchain>=0.2.5",
        "langchain-openai>=0.0.2",
        "openai>=1.6.1",
        "faiss-cpu>=1.7.4",
        "sentence-transformers>=2.2.2",
        "numpy>=1.24.3",
        "python-dotenv>=1.0.0",
        "pypdf>=3.17.0",
        "streamlit>=1.37.0",
    ],
)