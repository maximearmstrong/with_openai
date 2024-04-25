import os
from filelock import FileLock
import pickle

from dagster import (
    FilesystemIOManager,
    ConfigurableIOManager,
    AssetKey,
    InputContext,
    OutputContext
)
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.faiss import FAISS

class SearchIndexIOManager(ConfigurableIOManager):
    root_path: str

    def _get_path(self, asset_key: AssetKey) -> str:
        return self.root_path + "/".join(asset_key.path)

    def handle_output(self, context: OutputContext, obj):
        output_path = self._get_path(context.asset_key)
        with FileLock(output_path):
            if os.path.getsize(output_path) > 0:
                with open(output_path, "rb") as f:
                    serialized_search_index = pickle.load(f)
                cached_search_index = FAISS.deserialize_from_bytes(
                    serialized_search_index, OpenAIEmbeddings()
                )
                obj.merge_from(cached_search_index)

            with open(output_path, "wb") as f:
                pickle.dump(obj.serialize_to_bytes(), f)

    def load_input(self, context: InputContext):
        input_path = self._get_path(context.asset_key)
        with open(input_path, "rb") as f:
            serialized_search_index = pickle.load(f)
        return FAISS.deserialize_from_bytes(serialized_search_index, OpenAIEmbeddings())


fs_io_manager = FilesystemIOManager()
search_index_io_manager = SearchIndexIOManager(root_path="/tmp/")
