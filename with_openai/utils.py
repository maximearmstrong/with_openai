import os
import pathlib
import tempfile
import subprocess

import requests
from langchain.docstore.document import Document


def get_wiki_data(title, first_paragraph_only):
    url = f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&explaintext=1&titles={title}"
    if first_paragraph_only:
        url += "&exintro=1"
    data = requests.get(url).json()
    return Document(
        page_content=next(iter(data["query"]["pages"].values()))["extract"],
        metadata={"source": f"https://en.wikipedia.org/wiki/{title}"},
    )


def get_github_docs(repo_owner, repo_name, category):
    with tempfile.TemporaryDirectory() as d:
        #repo = Repo.clone_from(f"https://github.com/{repo_owner}/{repo_name}.git", d, depth=1)
        #git_sha = repo.rev_parse("HEAD").hexsha
        subprocess.check_call(
            f"/usr/bin/git clone --depth 1 https://github.com/{repo_owner}/{repo_name}.git .",
            cwd=d,
            shell=True,
        )
        git_sha = (
            subprocess.check_output("/usr/bin/git rev-parse HEAD", shell=True, cwd=d).decode("utf-8").strip()
        )
        docs_path = pathlib.Path(os.path.join(d, "docs/content", category))
        markdown_files = list(docs_path.glob("*.md*")) + list(docs_path.glob("*/*.md*"))
        for markdown_file in markdown_files:
            with open(markdown_file, "r") as f:
                relative_path = markdown_file.relative_to(d)
                github_url = (
                    f"https://github.com/{repo_owner}/{repo_name}/blob/{git_sha}/{relative_path}"
                )
                yield Document(page_content=f.read(), metadata={"source": github_url})
