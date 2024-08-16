import re
import json
from exa_py import Exa
import requests
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

DEBUG = True


def extract_citations(latex_content):
    citation_pattern = r"\\cite{([^}]*)}"
    return re.findall(citation_pattern, latex_content)


def get_citation_context(latex_content, citation, context_size=100):
    citation_pattern = r"\\cite{" + re.escape(citation) + r"}"
    match = re.search(citation_pattern, latex_content)
    if match:
        start = max(0, match.start() - context_size)
        end = min(len(latex_content), match.end() + context_size)
        context = latex_content[start:end]

        left_context = context[: match.start() - start]
        right_context = context[match.end() - start :]
        left_citation = re.search(r"\\cite{", left_context[::-1])
        if left_citation:
            left_context = left_context[-left_citation.start() :]
        right_citation = re.search(r"\\cite{", right_context)
        if right_citation:
            right_context = right_context[: right_citation.start()]

        return left_context + citation_pattern + right_context
    return ""


def search_exa_api(citation, context):
    exa = Exa(api_key="be68f0d7-bc15-47dc-b873-201a3b17f97f")
    result = exa.search_and_contents(
        f"{citation} {context}",
        type="neural",
        num_results=1,
        text=True,
        category="research paper",
        include_domains=["arxiv.org"],
    )
    return result


def arxiv_to_bibtex(arxiv_id, title):
    # try arxiv 2 bibtex instead
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    response = requests.get(url)
    if response.status_code == 200:
        xml = response.text
        print(xml)
        paper_title = re.search(r"<title>(.*?)</title>", xml)
        authors = re.findall(r"<name>(.*?)</name>", xml)
        year = re.search(r"<published>(\d{4})", xml)
        month = re.search(r"<published>\d{4}-(\d{2})", xml)
        abstract = re.search(r"<abstract>(.*?)</abstract>", xml, re.DOTALL)

        bibtex = f"@article{{{title},\n"
        if paper_title:
            bibtex += f"  Title = {{{paper_title.group(1)}}},\n"
        if authors:
            bibtex += f"  Author = {{{' and '.join(authors)}}},\n"
        if year:
            bibtex += f"  Year = {{{year.group(1)}}},\n"
        if month:
            bibtex += f"  Month = {{{month.group(1)}}},\n"
        bibtex += f"  Eprint = {{{arxiv_id}}},\n"
        bibtex += "  ArchivePrefix = {arXiv},\n"
        if abstract:
            bibtex += f"  Abstract = {{{abstract.group(1).strip()}}}\n"
        bibtex += "}"
        return bibtex
    return None


def process_latex_file(latex_file_path, bib_file_path):
    # Read existing BibTeX file
    with open(bib_file_path, "r", encoding="utf-8") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    # Extract titles from BibTeX entries
    existing_entries = [entry.get("ID", "") for entry in bib_database.entries]

    # Read LaTeX file
    with open(latex_file_path, "r", encoding="utf-8") as file:
        latex_content = file.read()

    citations = list(set(extract_citations(latex_content)))

    citations_to_process = [
        citation for citation in citations if citation.lower() not in existing_entries
    ]

    print(citations_to_process)
    if DEBUG:
        citations_to_process = citations_to_process[:20]

    title_to_arxiv_ids = {}
    for citation in citations_to_process[:2]:
        context = get_citation_context(latex_content, citation)
        with open("to_find.txt", "a", encoding="utf-8") as f:
            f.write(f"{citation}\n{context}\n\n")

        """

        exa_results = search_exa_api(citation, context)
        print(exa_results.results)

        if exa_results and exa_results.results:
            first_result = exa_results.results[0]
            arxiv_id = first_result.id.split("/")[-1]
            title_to_arxiv_ids[citation] = arxiv_id"""

    # Output the title_to_arxiv_ids dictionary to a file
    output_file_path = "title_to_arxiv_ids.json"
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        json.dump(title_to_arxiv_ids, output_file, indent=2)

    print(f"Title to arXiv ID mapping saved to {output_file_path}")


latex_file_path = "thesis.tex"
bib_file_path = "references.bib"
process_latex_file(latex_file_path, bib_file_path)
print(f"Updated BibTeX file saved to {bib_file_path}")
