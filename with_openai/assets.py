import os
import pickle

from dagster import (
    AssetExecutionContext,
    Config,
    StaticPartitionsDefinition,
    asset,
    define_asset_job,
)
from dagster_openai import OpenAIResource
from filelock import FileLock
from langchain.chains.qa_with_sources import stuff_prompt
from langchain_openai.chat_models.openai import ChatOpenAI
from langchain.docstore.document import Document
from langchain_openai.embeddings.openai import OpenAIEmbeddings
from langchain.schema.output_parser import StrOutputParser
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS

from .constants import SEARCH_INDEX_FILE, SUMMARY_TEMPLATE
from .utils import get_github_docs

docs_partitions_def = StaticPartitionsDefinition(
    [
        "about",
        "community",
        "concepts",
        "dagster-plus",
        "deployment",
        "getting-started",
        "guides",
        "integrations",
        "tutorial",
    ]
)


@asset(compute_kind="GitHub", partitions_def=docs_partitions_def, io_manager_key="fs_io_manager")
def source_docs(context: AssetExecutionContext):
    return list(get_github_docs("dagster-io", "dagster", context.partition_key))


@asset(compute_kind="OpenAI", partitions_def=docs_partitions_def, io_manager_key="search_index_io_manager")
def search_index(context: AssetExecutionContext, openai: OpenAIResource, source_docs):
    source_chunks = []
    splitter = CharacterTextSplitter(separator=" ", chunk_size=1024, chunk_overlap=0)
    for source in source_docs:
        context.log.info(source)
        for chunk in splitter.split_text(source.page_content):
            source_chunks.append(Document(page_content=chunk, metadata=source.metadata))

    with openai.get_client(context) as client:
        search_index = FAISS.from_documents(
            source_chunks, OpenAIEmbeddings(client=client.embeddings)
        )

    return search_index


class OpenAIConfig(Config):
    model: str
    question: str


@asset(compute_kind="OpenAI", io_manager_key="fs_io_manager")
def completion(
    context: AssetExecutionContext,
    openai: OpenAIResource,
    config: OpenAIConfig,
    search_index
):
    with openai.get_client(context) as client:
        prompt = stuff_prompt.PROMPT
        model = ChatOpenAI(client=client.chat.completions, model=config.model, temperature=0)
        summaries = " ".join(
            [
                SUMMARY_TEMPLATE.format(content=doc.page_content, source=doc.metadata["source"])
                for doc in search_index.similarity_search(config.question, k=4)
            ]
        )
        output_parser = StrOutputParser()
        chain = prompt | model | output_parser
        context.log.info(chain.invoke({"summaries": summaries, "question": config.question}))


search_index_job = define_asset_job(
    "search_index_job",
    selection="*search_index",
    partitions_def=docs_partitions_def,
)


question_job = define_asset_job(
    name="question_job",
    selection="completion",
)
