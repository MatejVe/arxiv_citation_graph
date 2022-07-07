import sqlite3
from habanero import Crossref
import feedparser
import urllib.request as libreq
import time

from numpy import average

def crossref_API_query(doi):
    """_summary_
    dict_keys(['indexed', 'reference-count', 'publisher', 'license', 
    'content-domain', 'short-container-title', 'published-print', 'DOI', 
    'type', 'created', 'page', 'source', 'is-referenced-by-count', 'title', 
    'prefix', 'author', 'member', 'reference', 'container-title', 
    'original-title', 'link', 'deposited', 'score', 'resource', 'subtitle', 
    'short-title', 'issued', 'references-count', 'URL', 'relation', 'ISSN', 
    'issn-type', 'published'])  
    Args:
        doi (_type_): _description_
    """
    OF_INTEREST = ["DOI", "title", "author", "URL"]
    cr = Crossref()
    work = cr.works(ids=doi)
    metadata = {}
    metadata["DOI"] = work["message"]["DOI"]
    try:
        metadata["title"] = work["message"]["title"][0] # Need [0] because for some reason the title comes back in a list
    except IndexError:
        pass

    try:
        authors = work["message"]["author"]
        metadata["authors"] = [{"name":author["given"] + ' ' + author["family"]} for author in authors]
    except KeyError:
        pass
    metadata["URL"] = work["message"]["URL"]
    return metadata

def arxiv_API_query(arxivID):
    OF_INTEREST = ["id", "title", "authors", "link"]

    base_url = "http://export.arxiv.org/api/query?"

    query = "id_list=%s" %arxivID

    with libreq.urlopen(base_url + query) as url:
        response = url.read()

    feed = feedparser.parse(response)
    entry = feed.entries[0]

    metadata = {}
    metadata["arxiv id"] = entry.id.split("/abs")[-1]
    metadata["title"] = entry["title"]
    metadata["authors"] = entry["authors"]
    for link in entry.links:
        if link.rel == "alternate":
            metadata["URL"] = link.href
    
    return metadata

con = sqlite3.connect('test.db')
cur = con.cursor()

# Get distinct papers
paperIds = []
for row in cur.execute('SELECT DISTINCT paper_id FROM reference_tree'):
    paperIds.append(row[0])

# Extract metadata for all the references in a paper
times = []

for ID in paperIds:
    time1 = time.time()
    for i, row in enumerate(cur.execute('SELECT paper_id, reference_type, reference_identificator FROM reference_tree WHERE paper_id="%s"' % ID)):
        tip = row[1]
        ref_id = row[2]
        if tip=='crossDOI' or tip=='doi':
            meta_data = crossref_API_query(ref_id)
        elif tip=='faid' or tip=='said':
            meta_data = arxiv_API_query(ref_id)
        else:
            raise ValueError()
    time2 = time.time()
    deltaTime = time2 - time1
    times.append(deltaTime)
    print(f'ArXiv ID: {ID}, number of references: {i+1}, time taken: {deltaTime:.2f}s.')
print(f'Average time to extract metadata: {average(times):.2f}s.')