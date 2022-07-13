import gzip
import os
import re
import shutil
import sqlite3
import tarfile
import time
import urllib.error
import urllib.request
import chardet
import feedparser

from arxiv_regex.arxiv_regex import *
from habanero import Crossref
import time

SOURCE_FOLDER = "dummy"

# random set of 100 arxiv_ids for test purposes
list_of_paper_ids = [
    "1902.00678",
    "1009.3615",
    "2010.07848",
    "1903.12466",
    "1711.07930",
    "1103.5007",
    "0712.2987",
    "1904.11042",
    "1207.4206",
    "1208.3840",
    "1703.05187",
    "math/0103136",
    "1403.2332",
    "astro-ph/9807138",
    "1909.03570",
    "1005.2643",
    "hep-th/9211122",
    "1609.06992",
    "1912.10120",
    "1502.04754",
    "1202.2111",
    "1104.5500",
    "1609.08371",
    "hep-ph/0310355",
    "1503.03173",
    "1810.04397",
    "1805.03513",
    "1309.0978",
    "1401.6046",
    "1409.3059",
    "1710.05019",
    "1404.1447",
    "1903.03180",
    "1802.03165",
    "2001.01322",
    "1710.09529",
    "1502.00299",
    "astro-ph/0506288",
    "nlin/0302024",
    "0905.2399",
    "1304.2052",
    "1905.04701",
    "1904.08907",
    "2006.08297",
    "2007.15443",
    "1901.10752",
    "hep-th/0311063",
    "1106.4244",
    "hep-ph/9703423",
    "astro-ph/0101271",
    "1605.02385",
    "0908.2474",
    "1610.04816",
    "1901.00305",
    "math-ph/0303034",
    "2002.04537",
    "astro-ph/0103457",
    "1109.2121",
    "1910.12428",
    "astro-ph/0612412",
    "1308.2522",
    "1207.3295",
    "1004.3144",
    "1205.3462",
    "1403.3472",
    "1301.2166",
    "1412.8760",
    "1511.09203",
    "1101.5836",
    "1201.3647",
    "1809.03310",
    "1105.0077",
    "1506.01015",
    "1511.07754",
    "0807.3419",
    "1710.04484",
    "1701.02355",
    "1811.03980",
    "1202.6581",
    "1810.02371",
    "1012.2079",
    "astro-ph/9808217",
    "2104.04052",
    "1305.1964",
    "1909.03906",
    "1709.03376",
    "1709.07867",
    "2103.07040",
    "1012.5654",
    "2011.00593",
    "1409.1557",
    "1710.03830",
    "1902.05953",
    "1012.2145",
    "1008.4706",
    "hep-ex/9908044",
    "1111.3549",
    "1811.12551",
    "cond-mat/0203121",
    "gr-qc/9401023",
]

subset_of_papers_ids = [
    "astro-ph/0101271",
    "1605.02385",
    "0908.2474",
    "1610.04816",
    "1901.00305",
]

test_paper = ["math-ph/0303034"]


def create_database():
    """
    This function takes the arxiv ids above, downloads the files for this
    paper (get_file), and extracts the citations (get_citations)

    Depending on what the id is returned metadata is different.
    Arxiv metadata:
        arxiv_id
        title
        authors (list of authors)
        URL (link)
        published (date)
        summary (abstract)
        arxiv_comment (Can contain information on where the article was published)
        arxiv_primary_category
        time_taken

    Crossref metadata:
        DOI
        title
        authors
        URL
        published (only year)
        type (journal-article, book, ...)
        container (where it was published)
        score (if it was a reference match, if it was queried through a doi there is no score)
        time_taken

    Common metadata:
        title, authors, URL, published, time_taken
    Arxiv specific:
        arxiv_id, summary, arxiv_comment, arxiv_primary_category
    Crossref specific:
        DOI, type, container, score
    """
    COMMON_FIELDS = ["title", "author", "URL", "published"]
    ARXIV_FIELDS = ["arxiv_id", "summary", "arxiv_comment", "arxiv_primary_category"]
    CROSSREF_FIELDS = ["DOI", "type", "container", "score"]
    con = sqlite3.connect("cleaned_table.db")
    cur = con.cursor()
    cur.execute(
        """CREATE TABLE reference_tree
                (paper_id, 
                reference_num, 
                id_type,
                reference_id, 
                title, 
                authors, 
                URL, 
                published,
                summary,
                arxiv_comment,
                arxiv_primary_category,
                type,
                container,
                score,
                length_of_bibitem,
                time_taken,
                bibitem
                )"""
    )

    for i, paper_id in enumerate(list_of_paper_ids):
        print("process paper %s, %d" % (paper_id, i))
        filename, list_of_files = get_file(paper_id)
        if list_of_files:
            citations_data, bibitems = get_citations(list_of_files)
            # Here we will store the citations in the database
            # citations should contain a reliable list of identifiers,
            # such as dois or arxiv_ids
            for i, metadata in enumerate(citations_data):
                title = metadata["title"]
                authors = metadata["authors"]
                URL = metadata["URL"]
                published = metadata["published"]
                time_taken = metadata["time_taken"]

                if "arxiv_id" in metadata.keys():
                    tip = "arxiv_id"
                    ident = metadata["arxiv_id"]
                    summary = metadata["summary"]
                    arxiv_comment = metadata["arxiv_comment"]
                    arxiv_category = metadata["arxiv_primary_category"]
                    # Set the crossref categories to null
                    item_type = "null"
                    container = "null"
                    score = "null"
                elif "DOI" in metadata.keys():
                    tip = "crossDOI"
                    ident = metadata["DOI"]
                    item_type = metadata["type"]
                    container = metadata["container"]
                    if (
                        "score" in metadata.keys()
                    ):  # Some items don't have score - identified through a doi
                        score = metadata["score"]
                    else:
                        score = "null"
                    # Set the arxiv categories to null
                    summary = "null"
                    arxiv_comment = "null"
                    arxiv_category = "null"

                cur.execute(
                    "INSERT INTO reference_tree VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        paper_id,
                        i,
                        tip,
                        ident,
                        title,
                        authors,
                        URL,
                        published,
                        summary,
                        arxiv_comment,
                        arxiv_category,
                        item_type,
                        container,
                        score,
                        len(bibitems[i]),
                        time_taken,
                        bibitems[i],
                    ),
                )  # tip is Croatian for type, can't use type since it is a reserved keyword
                con.commit()

        # To avoid running out of disk space we delete everything imediately
        if os.path.exists(filename + ".tar"):
            print("Delete tar file")
            os.remove(filename + ".tar")
        if os.path.exists(filename + ".folder_dummy"):
            print("Delete folder %s.folder_dummy" % filename)
            shutil.rmtree(filename + ".folder_dummy")
    con.close()
    return


def get_file(paper_id):
    """
    Returns a list of files which could contain citation information.
    We use all .tex and .bbl files
    """
    url = "http://export.arxiv.org/e-print/%s" % paper_id
    filename = SOURCE_FOLDER + "/%s" % paper_id.replace(".", "_").replace("/", "_")
    rawdata = retrieve_rawdata(url)
    if rawdata is not None:
        unpack_rawdata(rawdata, filename)

        # get all files
        all_files = []
        for path, subdirs, files in os.walk(filename + ".folder_dummy"):
            for name in files:
                all_files.append(os.path.join(path, name))
        # get all .bbl files
        list_of_files = [
            f for f in all_files if (f.endswith(".bbl") or f.endswith(".tex"))
        ]
        print("list_of_files = ", list_of_files)
        return filename, list_of_files
    else:
        return filename, []


def retrieve_rawdata(url):
    """
    This function gets the data from a web location and returns the
    raw data
    """
    retries = 0
    while retries < 3:
        try:
            # response = requests.get(url)
            with urllib.request.urlopen(url) as response:
                rawdata = response.read()
            return rawdata
        except urllib.error.HTTPError as e:
            sleep_sec = int(e.hdrs.get("retry-after", 30))
            print("WARNING: Got %d. Retrying after %d seconds." % (e.code, sleep_sec))
            time.sleep(sleep_sec)
            if e.code == 503:
                retries += 1
                continue
            elif e.code == 403:
                # Forbidden: the server understood the request but refuses to authorize it.
                # Re-authenticating will make no difference. The access is permanently forbidden
                # and tied to the application logic, such as insufficient rights to a resource.
                return None
            else:
                raise
    print("WARNING: No success after %d retries" % retries)
    return None


def unpack_rawdata(rawdata, filename):
    """
    This function checks what kind of data we got and writes it
    into the target_folder
    """
    target_folder = filename + ".folder_dummy"
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)

    if rawdata[0:2] == b"%P":
        print(
            "Seems to be a doc file, so far no processing of doc files has been implemented"
        )
    else:
        with open(filename + ".tar", "wb") as file:
            file.write(rawdata)

        try:
            tar = tarfile.open(filename + ".tar")
            tar.extractall(path=target_folder)
            tar.close()
        except:
            data = gzip.decompress(rawdata)
            file_ = open(target_folder + "/dummy.tex", "wb")
            file_.write(data)
            file_.close()
    return


def get_citations(list_of_files):
    """
    This function starts with a list of files which could contain
    citation information and returns a list of arxiv_ids
    """
    citations = []
    bibitems = []
    for filename in list_of_files:
        print(f"Looking into {filename}.")
        contents = get_data_string(filename)
        # Check whether we have citation information in this file
        if contents.find(r"\bibitem") > -1:
            # remove the text before the first appearance of '\bibitem'
            # and after the appearance of '\end{thebibliography}
            first_bibitem = contents.find(r"\bibitem")
            bibliography_end = contents.find(r"\end{thebibliography}")
            contents = contents[first_bibitem:bibliography_end]

            # split by bibitem to get a list of citations
            list_of_bibitems = contents.split(r"\bibitem")
            # Filter the list of empty '' tags
            list_of_bibitems = list(filter(lambda item: item, list_of_bibitems))
            # Strip the empty spaces
            list_of_bibitems = [item.strip() for item in list_of_bibitems]
            print(f"Found {len(list_of_bibitems)} references.")

            for i, bibitem in enumerate(list_of_bibitems):
                print(f"Processing reference number {i}.")

                # for each citation check whether there is an doi tag
                # Since DOI is a strong identifier and the regex doesn't
                # seem to be producing false positives we save the doi
                results_doi = check_for_doi(bibitem)
                # TODO: rewrite this code logic when you think of something better
                # next we do a strict arxiv id check
                # strict arxiv is reliable and if there is a strict arxiv id then save it
                strict_arxiv_id = check_for_arxiv_id_strict(bibitem)
                # finally do a flexible arxiv id check
                flexible_arxiv_id = check_for_arxiv_id_flexible(bibitem)

                if results_doi:
                    # for some reason it comes back in a list
                    results_doi = results_doi[0]
                    print(f"Found a DOI.")
                    try:  # In come cases the extracted DOI is faulty and will return an error
                        if check_doi_registration_agency(results_doi) == "Crossref":
                            md = crossref_metadata_from_doi(results_doi)
                    except:
                        print(f"DOI couldn't be resolved, querying CrossRef.")
                        # Clean up the bibitem before sending it to crossref
                        # Might perform better
                        bibitem = clean_up_bibtex(bibitem)
                        md = crossref_metadata_from_query(bibitem)
                    citations.append(md)
                    bibitems.append(bibitem)

                elif strict_arxiv_id:
                    strict_arxiv_id = clean_arxiv_id(strict_arxiv_id[0])
                    print(f"Found an arXiv ID (strict) {strict_arxiv_id}.")
                    md = arxiv_metadata_from_id(strict_arxiv_id)
                    citations.append(md)
                    bibitems.append(bibitem)

                elif flexible_arxiv_id:
                    flexible_arxiv_id = clean_arxiv_id(flexible_arxiv_id[0])
                    print(f"Found an arXiv ID (flexible) {flexible_arxiv_id}.")
                    md = arxiv_metadata_from_id(flexible_arxiv_id)
                    citations.append(md)
                    bibitems.append(bibitem)

                else:
                    # If all of these methods fail we need to utilize some other method
                    # We use crossref and their reference matching system
                    # See https://www.crossref.org/categories/reference-matching/#:~:text=Matching%20(or%20resolving)%20bibliographic%20references,indexes%2C%20impact%20factors%2C%20etc.
                    time1 = time.time()
                    # Clean up the bibitem before sending it to crossref
                    # Might perform better
                    bibitem = clean_up_bibtex(bibitem)
                    md = crossref_metadata_from_query(bibitem)
                    citations.append(md)
                    bibitems.append(bibitem)
                    time2 = time.time()
                    print(
                        f"Resorted to CrossRef, time taken to retrieve metadata: {time2-time1:.2f}s"
                    )

    return citations, bibitems


def get_data_string(filename):
    """
    Here we read the data file and decode the byte string
    """
    try:
        with open(filename, "rb") as f:
            contents = f.read()
    except:
        # So far we had no issue with this, but if it happens we should
        # catch the exception
        print("Can't read file?")
        raise
    else:
        # We need to check how this byte string is encoded
        detection = chardet.detect(contents)
        encoding = detection["encoding"]
        print("encoding = ", encoding)
        if encoding is None:
            # Let's try utf-8 and ignore any errors
            contents = contents.decode("utf-8", "ignore")
        else:
            # Even though we tried to determine the encoding above,
            # it still happens that we get errors here
            contents = contents.decode(encoding, "ignore")
        return contents


def check_for_arxiv_id_strict(citation: str) -> list[str]:
    """
    Strict regex for finding arxiv ids. This will essentially only match if the
    format of the arxiv id is exactly as specified https://arxiv.org/help/arxiv_identifier
    Seems to have no false positives but on the other hand it doesn't detect a lot of
    arxiv ids

    Args:
        citation (str): a full bibtex entry of the citation

    Returns:
        list of strings: each field corresponds to a group hit in the defined regex
    """
    raw_hits = re.findall(REGEX_ARXIV_STRICT, citation)
    # every hit is a tuple whose entries correspond to the regex groups of the expression
    # we need to find which group produced a hit
    # TODO: find better naming for all this
    hits = []
    for hit in raw_hits:
        for group in hit:
            if group:
                hits.append(group.lower())
    return list(set(hits))


def check_for_arxiv_id_flexible(citation: str) -> list[str]:
    """
    Flexible regex for finding arxiv ids. As specified in the arxiv_regex.py:
    this regex essentially accepts anything that looks like an arxiv id and has
    the slightest smell of being one as well. that is, if it is an id and
    mentions anything about the arxiv before hand, then it is an id.

    Args:
        citation (str): a full bibtex entry of the citation

    Returns:
        list of strings: each field corresponds to a group hit in the defined regex
    """
    raw_hits = re.findall(REGEX_ARXIV_FLEXIBLE, citation)
    # every hit is a tuple whose entries correspond to the regex groups of the expression
    # we need to find which group produced a hit
    # TODO: come up with better naming conventions for all this
    hits = []
    for hit in raw_hits:
        for group in hit:
            if group:
                hits.append(group.lower())
    return list(set(hits))


def clean_arxiv_id(id: str) -> str:
    """
    Some references contain faulty arxiv ids. Example: arXiv:math.PR/0003156
    '.PR' part breaks the lookup function. Subcategories can't be appended
    to a category. This function cleans that up.

    Args:
        id (str): arxiv id that might contain faulty fields

    Returns:
        str: cleaned up arxiv id
    """
    if "/" in id:
        cat, num = id.split("/")
        if "." in cat:
            cat = cat.split(".")[0]
        return cat + "/" + num
    return id


def arxiv_metadata_from_id(arxivID: str) -> dict:
    """
    Provided a valid arxivID this function will query the arxiv API
    and parse the response. The function returns a dictionary with
    the items of interest.

    Metadata that we are currently interested in:
        arxiv_id,
        title,
        authors,
        link,
        published,
        summary,
        arxiv_comment,
        arxiv_primary_category

    Additionally, we store time_taken which is the amount of time
    taken to get a response from the API

    Args:
        arxivID (str): a valid arXiv ID

    Returns:
        dict: a dictionary with keys being the fields we are
                interested in above
    """
    OF_INTEREST = [
        "arxiv_id",
        "title",
        "authors",
        "link",
        "published",
        "summary",
        "arxiv_comment",
        "arxiv_primary_category",
    ]
    SIMPLE_EXTRACT = ["title", "summary", "arxiv_comment"]

    base_url = "http://export.arxiv.org/api/query?"

    query = "id_list=%s" % arxivID

    time1 = time.time()
    response = retrieve_rawdata(base_url + query)
    time2 = time.time()

    feed = feedparser.parse(response)
    entry = feed.entries[0]

    metadata = {}
    # Extract the simple entries
    for item in SIMPLE_EXTRACT:
        try:
            metadata[item] = entry[item]
        except KeyError:
            metadata[item] = "null"

    # Extract entries that require some postprocessing
    try:
        metadata["arxiv_id"] = entry.id.split("/abs/")[-1]
    except KeyError:
        metadata["arxiv_id"] = "null"

    try:
        metadata["published"] = entry["published"].split("-")[0]
    except:
        metadata["published"] = "null"

    try:
        authors = entry["authors"]
        metadata["authors"] = ", ".join([author["name"] for author in authors])
    except KeyError:
        metadata["authors"] = "null"

    try:
        for link in entry.links:
            if link.rel == "alternate":
                metadata["URL"] = link.href
    except KeyError:
        metadata["URL"] = "null"

    try:
        metadata["arxiv_primary_category"] = entry["arxiv_primary_category"]["term"]
    except KeyError:
        metadata["arxiv_primary_category"] = "null"

    metadata["time_taken"] = time2 - time1

    return metadata


def check_for_doi(citation: str) -> list[str]:
    """
    This function returns dois using regular expressions. So far I haven't seen
    false positive with this selection.
    Note that while this regular expression matches most dois, it does not match
    all of them. For more details see
    https://www.crossref.org/blog/dois-and-matching-regular-expressions/

    Args:
        citation (str): string that is the full citation,
                        usually a full bibtex item

    Returns:
        list: a list of strings of unique matches
    """
    pattern = re.compile("10.\\d{4,9}/[-._;()/:a-z0-9A-Z]+", re.IGNORECASE)
    return list(set(re.findall(pattern, citation)))


def check_doi_registration_agency(doi: str) -> str:
    """
    This function takes a DOI and queries crossref to check where the doi
    is registered. If it is registered at crossref we can get metadata from
    crossref. If it isn't registered with crossref some other methods will
    have to be utilized.

    Args:
        doi (str): a valid DOI identifier

    Returns:
        str: registration agency the DOI is registered with
    """
    cr = Crossref()
    return cr.registration_agency(doi)[0]


def crossref_metadata_from_doi(doi: str) -> dict:
    """
    Provided a valid doi this function will query the CrossRef API
    and parse the returned metadata. The function returns a dictionary
    with the items of interest.

    Metadata we are interested in:
        DOI
        title
        author
        URL
        published
        type
        container

    Full list of possible categories:
    ['indexed', 'reference-count', 'publisher', 'license',
    'content-domain', 'short-container-title', 'published-print', 'DOI',
    'type', 'created', 'page', 'source', 'is-referenced-by-count', 'title',
    'prefix', 'author', 'member', 'reference', 'container-title',
    'original-title', 'link', 'deposited', 'score', 'resource', 'subtitle',
    'short-title', 'issued', 'references-count', 'URL', 'relation', 'ISSN',
    'issn-type', 'published']

    Additionally we store time_taken which is the amount of time taken to get
    a response from the CrossRef REST API.

    Args:
        doi (str): a valid DOI identifier

    Returns:
        dict: a dictionary with keys that correspond to fields we are interested in
                above
    """
    OF_INTEREST = ["DOI", "title", "author", "URL", "published", "type", "container"]
    SIMPLE_EXTRACT = ["DOI", "URL", "type"]

    time1 = time.time()
    cr = Crossref(mailto="matejvedak@gmail.com")
    work = cr.works(ids=doi)["message"]
    time2 = time.time()

    metadata = {}
    # Extract simple entries
    for item in SIMPLE_EXTRACT:
        try:
            metadata[item] = work[item]
        except KeyError:
            metadata[item] = "null"

    # Extract entries that require some postprocessing
    try:
        # Need [0] because for some reason the title comes back in a list
        metadata["title"] = work["title"][0]
    except IndexError:
        metadata["title"] = "null"

    try:
        authors = work["author"]
        metadata["authors"] = ", ".join(
            [author["given"] + " " + author["family"] for author in authors]
        )
    except KeyError:
        metadata["authors"] = "null"

    try:
        metadata["published"] = work["published"]["date-parts"][0][0]
    except KeyError:
        metadata["published"] = "null"

    try:
        metadata["container"] = work["container-title"][0]
    except KeyError:
        metadata["container"] = "null"

    metadata["time_taken"] = time2 - time1

    return metadata


def crossref_metadata_from_query(bibitem: str) -> dict:
    """
    This is function that utilizes the habanero module to communicate with the
    crossref API. Given bibitem is processed on the crossref servers which try
    to match a reference to one of the works in their database. Subsequently,
    metadata about the reference can be extracted back.

    One issue is that crossref will always try to match a work to a reference,
    so even if a reference doesn't exist crossref will find something.

    The function returns a dictionary with the items we are interested in.

    Fields we are interested in:
        DOI,
        title,
        authors,
        URL,
        published,
        type,
        container,
        score

    Full list of available fields:
    ['indexed', 'reference-count', 'publisher', 'license',
    'content-domain', 'short-container-title', 'published-print', 'DOI',
    'type', 'created', 'page', 'source', 'is-referenced-by-count', 'title',
    'prefix', 'author', 'member', 'reference', 'container-title',
    'original-title', 'link', 'deposited', 'score', 'resource', 'subtitle',
    'short-title', 'issued', 'references-count', 'URL', 'relation', 'ISSN',
    'issn-type', 'published']

    Additionally we store time_taken which is the amount of time taken to get
    a response from the CrossRef REST API.

    Args:
        bibitem (str): full bibtex entry of the wanted reference

    Returns:
        dict: a dictionary with keys that correspond to fields we are interested in
                above
    """
    OF_INTEREST = [
        "DOI",
        "title",
        "authors",
        "URL",
        "published",
        "type",
        "container",
        "score",
    ]
    SIMPLE_EXTRACT = ["DOI", "URL", "type", "score"]

    time1 = time.time()
    cr = Crossref(mailto="matejvedak@gmail.com")
    x = cr.works(query_bibliographic=bibitem, limit=1)
    time2 = time.time()

    if x["message"]["items"]:
        bestItem = x["message"]["items"][0]

        metadata = {}
        # Extract the simple items
        for item in SIMPLE_EXTRACT:
            try:
                metadata[item] = bestItem[item]
            except:
                metadata[item] = "null"

        # Extract the items that require postprocessing
        try:
            metadata["title"] = bestItem["title"][0]
        except KeyError:
            metadata["title"] = "null"

        try:
            authors = bestItem["author"]
            metadata["authors"] = ", ".join(
                [author["given"] + " " + author["family"] for author in authors]
            )
        except KeyError:
            metadata["authors"] = "null"

        try:
            metadata["published"] = bestItem["published"]["date-parts"][0][0]
        except KeyError:
            metadata["published"] = "null"

        try:
            metadata["container"] = bestItem["container-title"][0]
        except KeyError:
            metadata["container"] = "null"

        metadata["time_taken"] = time2 - time1

    else:
        metadata = {item: "null" for item in OF_INTEREST}
        metadata["time_taken"] = time2 - time1

    return metadata

def clean_up_bibtex(bibitem: str) -> str:
    """
    This function cleans up a bibtex entry. It removes unnecessary characters in an 
    attempt to improve matching precision and improve matching speed.

    Currently it cleans up:

    Args:
        bibitem (str): full bibtex reference entry

    Returns:
        str: cleaned up bibtex reference entry
    """
    # Many bibtex items start with the local reference name enclosed within the '{}'
    # brackets. If they do start with '{' we can remove it immediatelly
    if bibitem[0] == '{':
        i = 1
        while bibitem[i] != '}':
            i += 1
        bibitem = bibitem[i:]    
    
    # Clean up latex items like \em{} etc
    pattern = re.compile(r"\\[A-z]+{")
    bibitem = re.sub(pattern, '', bibitem)
    # Clean up item like \newblock (items which don't utilize '{}')
    pattern = re.compile(r"\\[A-z]+")
    bibitem = re.sub(pattern, '', bibitem)
    # Remove '\n'
    pattern = re.compile(r"\n")
    bibitem = re.sub(pattern, '', bibitem)
    # Clean up simple characters: {}[]
    reduntant_characters = r"{}[]\"'"
    bibitem = bibitem.translate({ord(char):None for char in reduntant_characters}).strip()
    # Remove reduntant white space
    pattern = re.compile(r"\s{2,}")
    bibitem = re.sub(pattern, ' ', bibitem)

    return bibitem


time1 = time.time()
#create_database()
time2 = time.time()
print(f"It took me {time2-time1:.2f}s to process a 100 papers.")

# print(check_doi_registration_agency("10.1109/TAC.2018.2876389"))
# print(crossref_metadata_from_doi("10.1109/TAC.2018.2876389"))
# print(arxiv_metadata_from_id("1903.03180"))
# print(
#    crossref_metadata_from_query(
#        "Wooldridge, J. M. (2009). On estimating firm-level production functions using proxy variables to control for unobservables. Economics Letters, 104(3):112–114."
#    )
# )