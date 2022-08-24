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
import time

import feedparser
from habanero import Crossref
import untangle

from arxiv_regex.arxiv_regex import *

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
    "1012.2079",
    "astro-ph/9808217",
    "2104.04052",
    "1305.1964",
    "1909.03906",
    "1709.03376",
    "1709.07867",
    "2103.07040",
]

test_paper = ["1401.6046"]


class AttrDict(dict):
    """
    Type of dictionary that can't be assigned new keys to.
    A caveat is that the initialization of the dictionary is a bit different:
    keys = ["a", "b"]
    values = [1, 2]
    dict = AttrDict(zip(keys, values))

    The idea is to set a standard for a metadata dictionary so that later mistakes
    in assigning data can be avoided.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __setattr__(self, key, value):
        if key not in [*self.keys(), "__dict__"]:
            raise KeyError(f"No new keys allowed - {key}")
        else:
            super().__setattr__(key, value)

    def __setitem__(self, key, value):
        if key not in self:
            raise KeyError(f"No new keys allowed - {key}")
        else:
            super().__setitem__(key, value)


# Fields that can be stored have to be initialized here
# They are automatically filled with null, unless a non null
# value is assigned somewhere else in the code
FIELDS_TO_STORE = [
    "paper_id",
    "reference_num",
    "status",
    "ref_arxiv_id",
    "DOI",
    "title",
    "abstract",
    "authors",
    "database_name",
    "last_modified_datetime",
    "created_datetime",
    "authors_linked",
    "authors_linked_short",
    "pdf_link",
    "source_link",
    "arxiv_comment",
    "arxiv_primary_category",
    "type",
    "container",
    "score",
    "length_of_bibitem",
    "time_taken",
    "bibitem",
    "clean_bibitem",
]


def create_default_md_dict(fields_to_store: list) -> AttrDict:
    values = ["Null"] * len(fields_to_store)
    return AttrDict(zip(FIELDS_TO_STORE, values))


def create_database(
    dbname,
    tableName,
    arxivIDs,
    mode="restAPI",
    email=None,
    threshold=0,
    xmlQueryNum=5,
    xmlUseRESTAPI=True,
):
    """
    This function takes the arxiv ids above, downloads the files for this
    paper (get_file), and extracts the citations (get_citations)

    There are a few parameters that modify how the script extacts the citations
    metadata. Here we breakdown all the function arguments.

        1. dbname - name of the database in which the data will be stored
        2. tableName - name of the table in which the data will be stored
        3. arxivIDs - list of arXiv papers that are to be processed
        4. mode - default "restAPI", other options are "neither" and "xmlAPI"
                    "restAPI" uses Crossref's JSON REST API to process references
                        that have no identifier within them
                    "neither" only processes the references with an identifier,
                        ignores the rest
                    "xmlAPI" uses Crossref's XML API to process references that
                        have no identifier within them
        5. email - defaults to None but really should be provided, user email that
                    is sent in the HTML GET request header to Crossref
        6. threshold - defaults to 0, signals how certain the JSON REST API has to be
                        in the matching, if the score of a matched reference is below
                        this threshold the matching will be overturned and reference
                        marked as "unresolved"
        7. xmlQueryNum - parameter that controls how many references are to be sent
                            at once to the XML server for processing. 5 references seem
                            to be a good number.
        8. xmlUseRESTAPI - True or False, defaults to True, controls whether we use the
                            JSON REST API to process references that the XML API couldn't
                            resolve.

    Currently defined columns are: paper_id, reference_num, status, ref_arxiv_id,
        DOI, title, abstract, authors, database_name, last_modified_datetime,
        authors_linked, authors_linked_short, pdf_link, source_link, arxiv_comment,
        arxiv_primary_category, type, container, score, length_of_bibitem, time_taken,
        bibitem, clean_bibitem
    To add a column just name it in the FIELDS_TO_STORE list above this.
    The default value of all fields is 'null', unless some value is assigned.
    This will probably need to be changed - just amend the value in the
    "create_default_md_dict" function.

    Let's go through each field:
        1. paper_id - arxiv id of the paper where the reference was found
        2. reference_num - number of the reference within the paper
        3. status - resolved, unresolved or ignored. Resolved is for
                    fully processed references, unresolved if there was
                    an error or couldn't be resolved,
                    ignored if processing wasn't tried
        4. ref_arxiv_id - meant to be short for reference arxiv id,
                        arxiv identifier of the reference, if there is one
        5. DOI - doi identifier of a reference, if there is one
        6. title - title of the referenced work
        7. abstract - abstract of the referenced work, only the arxiv API
                    provides this
        8. authors - authors of the referenced work
        9. database_name - name of the database where the work is stored? contained?
                        currently only gets populated for arxiv references with the
                        value 'arxiv'. I imagine for biorxiv it will be populated
                        with 'biorxiv' and so on. I don't know what to put here
                        for DOI references though.
        10. last_modified_datetime - self explanatory. For crossref REST API queries
                                    this is populated with the "created" field.
                                    "created" field probably is probably when the
                                    work was deposited to crossref and probably
                                    isn't the last time the work was modified but
                                    for a lack of something better that is used.
                                    XML API doesn't provide that at all
        TODO:
        11. authors_linked - author string including links to the profile pages of users
                            NOT IMPLEMENTED
        12. authors_linked_short - author string trimmed to 8 authors including an et al.
                            NOT IMPLEMENTED
        13. pdf_link - mostly only for arxiv references. Capturing a DOI mostly
                        points to a URL in the form of a source and not the pdf itself.
        14. source_link - URL of the website of the reference
        15. arxiv_comment - comment relating to an arxiv paper. Can contain
                            information on where the paper was published
        16. arxiv_primary_category - hep-ex, math, cs-ai, etc.
        17. type - what type of work is it - journal article, book, conference paper, ...
        18. container - where is the work published/contained in? Journals, books, ...
        19. score - if queried with crossref REST API a score will be returned.
                    This score indicates how certain crossref is the match is correct.
                    In this paper https://essay.utwente.nl/73817/1/chenet_MA_EEMCS.pdf
                    the author claims that only scores above a 120 are absolute matches.
                    Based on manual assesment I find it hard to believe this. I would say
                    almost all scores above 50 are matches, and a decent number of scores
                    above 30 are correct matches.
        20. length_of_bibitem - length of the clean bibitem used to query crossref
        21. time_taken - time taken to get a response from whatever server was queried
        22. bibitem - bibitem as extracted from the original paper
        23. clean_bibitem - bibitem cleaned up and made to look almost like a normal reference
                            See the clean_up_bibtex function for details on what was done.
    """
    con = sqlite3.connect(dbname)
    cur = con.cursor()

    # TODO: since Florian mentioned that SQLite is only used here as a
    # placeholder (the full code probably uses postgres?) this part will most
    # likely have to be ammended. A table will most likely have to be updated
    # instead of created from scratch and different fields will be populated
    # (see the first TODO below this one)
    # A parameter for the table name can, and probably should be added as well
    # since "reference_tree" is just a placeholder

    # delete the table if it already exists
    cur.execute("DROP TABLE IF EXISTS {};".format(tableName))
    cur.execute("CREATE TABLE {} ({})".format(tableName, ",".join(FIELDS_TO_STORE)))

    for i, paper_id in enumerate(arxivIDs):
        print("process paper %s, %d" % (paper_id, i))
        filename, list_of_files = get_file(paper_id)
        if list_of_files:
            citations_data, clean_bibitems, bibitems = get_citations(
                list_of_files,
                mode=mode,
                email=email,
                threshold=threshold,
                xmlQueryNum=xmlQueryNum,
                xmlUseRESTAPI=xmlUseRESTAPI,
            )
            # Here we will store the citations in the database
            # citations should contain a reliable list of identifiers,
            # such as dois or arxiv_ids
            for i, md in enumerate(citations_data):
                WHAT_GETS_ASSIGNED = [
                    "paper_id",
                    "reference_num",
                    "length_of_bibitem",
                    "bibitem",
                ]
                md["paper_id"] = paper_id
                # reference number will unfortunately get messed up
                # it won't be the same as the reference number in the paper
                md["reference_num"] = i + 1
                md["length_of_bibitem"] = len(clean_bibitems[i])
                md["clean_bibitem"] = clean_bibitems[i]
                md["bibitem"] = bibitems[i]

                # TODO: ammend the insert into command here which will work
                # with the database that is used in the final application
                QUESTIONMARKS = ",".join(["?"] * len(md))
                cur.execute(
                    "INSERT INTO {} VALUES ({})".format(tableName, QUESTIONMARKS),
                    tuple(md.values()),
                )
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
    time1 = time.time()
    retries = 0
    while retries < 3:
        try:
            # response = requests.get(url)
            with urllib.request.urlopen(url) as response:
                rawdata = response.read()
            time2 = time.time()
            print(f"It took me {time2-time1:.2f}s to retrieve data from {url}.")
            return rawdata
        except urllib.error.HTTPError as e:
            # From what I have seen, the only HTTP error that does happen (at least in the test set)
            # is with the XML server when for some references we get thrown a 'bad request'.
            # I don't know how to fix this bad request and waiting full 30 seconds for a certain outcome
            # of an error 400 is too much. This is why I changed this to 5 seconds, I don't know how
            # smart this is. I guess whoever mantains this code will have to judge for themselves.
            sleep_sec = int(e.hdrs.get("retry-after", 5))
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


def get_citations(
    list_of_files,
    mode="restAPI",
    email=None,
    threshold=0,
    xmlQueryNum=5,
    xmlUseRESTAPI=True,
):
    """
    This function starts with a list of files which could contain
    citation information and returns a list of arxiv_ids

    Args:
        mode: restAPI, xmlAPI, neither

        restAPI will query crossref REST API for any reference
        that has no identifier within.
        REST API has two types of servers: public pool and polite pool
        Request is handled by the public pool if no email is provided.
        This turned out to be quite fast, between 1s and 3s per reference.
        Request is handled by the polite pool if an email is provided.
        For some reason this takes much longer. Up to 10s per reference.
        Advantage of the polite pool is that crossref authors will send you an
        email if your script is behaving in a manner they don't like.
        With the public pool, you might simply be banned from accessing their
        services.
        Put your email in the email argument to get access to the polite
        pool.

        XML API will query crossref XML API with references that have no identifier
        within. The difference between XML API and REST API is that the XML API can
        fail to identify a reference - there is no scoring system. In case the reference
        couldn't be resolved, its bibtex will be saved with a tag 'unresolved'.
        These unresolved references can later be ran through the REST API or parsed
        with some custom built NLP parses, or whatever other method can be thought of.
        xmlQueryNum parameter needs to be an integer that specifies how many references
        at a time are requested from the XML server.
        Unfotunately, the XML part still works itchy. For some reason, a lot of requests
        cause a HTTPS 400 error - most likely caused by a bad request. I can't figure out
        what is causing this request defects. My bet is on some obscure characters that need
        to be removed from bibtex before querying it: for example the character '&' broke down
        a lot of request for some strange reason. I will investigate this and try to find
        which characters break the request but I most likely won't catch all of them.
        If xmlUseRESTAPI is set to True, all the unresolved refernces, whether by error 400
        or returned unresolved will be queried through the JSON REST API.

        neither option will simply skip all the unrecognized references. Only those with
        an arxiv id or a DOI will be recognized and their metadata extracted. Rest of the
        references will be saved within the same database (fields of paper_id, reference_num,
        status, bibitem, clean_bibitem will be populated). Status field will be 'ignored'.

        email: email to be used with crossref's JSON API and XML API, optional
        threshold: threshold score that crossref JSON API returns, matched references
                    below the threshold score are marked as unresolved
        xmlQueryNum: number of references for xml to query at once
        xmlUseRESTAPI: whether the XML API will use JSON API for references that have
                        been returned because of a 400 error (bad XML request).
                        Optional, defaults to True
    """
    citations = []
    clean_bibitems = []
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
            list_of_clean_bibitems = [clean_up_bibtex(bib) for bib in list_of_bibitems]

            identifiers = []
            for i, bibitem in enumerate(list_of_bibitems):
                print(f"Looking for identifiers in reference number {i}.")
                # Some bibitems come out just as '{}' for example ('stop[0]{}%')
                # We don't process these as it is obviously a faulty reference
                if len(bibitem) > 30:  # after processing all the test papers
                    # 30 was the limit above which actual
                    # references appeared
                    # for each citation check whether there is an doi tag
                    # Since DOI is a strong identifier and the regex doesn't
                    # seem to be producing false positives we save the doi
                    results_doi = check_for_doi(bibitem)
                    # next we do a strict arxiv id check
                    strict_arxiv_id = check_for_arxiv_id_strict(bibitem)
                    # finally do a flexible arxiv id check
                    flexible_arxiv_id = check_for_arxiv_id_flexible(bibitem)
                    # cleaned bibitems are used to query crossref
                    # hope it increases performance
                    clean_bibitem = list_of_clean_bibitems[i]
                    bibitems.append(bibitem)
                    clean_bibitems.append(clean_bibitem)
                    if results_doi:
                        # for some reason it comes back in a list
                        results_doi = results_doi[0]
                        # Some DOIs come back with the final character ';'
                        # This breaks the DOI and need to be removed
                        results_doi = (
                            results_doi[:-1] if results_doi[-1] == ";" else results_doi
                        )
                        print(f"Found a DOI: {results_doi}")
                        identifiers.append((i, results_doi, "DOI"))
                    elif strict_arxiv_id:
                        strict_arxiv_id = clean_arxiv_id(strict_arxiv_id[0])
                        print(f"Found an arXiv ID (strict) {strict_arxiv_id}.")
                        identifiers.append((i, strict_arxiv_id, "arxivID"))
                    elif flexible_arxiv_id:
                        flexible_arxiv_id = clean_arxiv_id(flexible_arxiv_id[0])
                        print(f"Found an arXiv ID (flexible) {flexible_arxiv_id}.")
                        identifiers.append((i, flexible_arxiv_id, "arxivID"))
                    else:
                        print("No identifier could be found.")
                        identifiers.append((i, None, None))

            # We have identifiers now and can extract metadata depending on the
            # mode parameter
            if mode == "restAPI":
                # TODO: this type of extraction allows for easy speeding up
                # we could easily first create lists of items depending on the 'tip'
                # and then, instead of one by one, query all arxivIDs at once.
                # See the arxiv_metadata_from_id function - in the line
                # 'query="id_list=%s" % arxivID' instead of a single ID
                # we can provide a sequence of IDs separated by a comma.
                # This would require a slight refactor of this function
                # and some refactoring in the arxiv_metadata_from_id function.
                # This route was not pursued since the arxiv api is not the
                # speed bottleneck of the whole script. Nonetheless, the option
                # is there.
                for num, ident, tip in identifiers:
                    print(
                        f"Extracting metadata for reference number {identifiers.index((num, ident, tip))}."
                    )
                    if tip == "DOI":
                        if check_doi_registration_agency(ident) == "Crossref":
                            md = crossref_metadata_from_doi(ident, email=email)
                        else:
                            md = crossref_metadata_from_query(
                                clean_bibitems[num], threshold=0, email=email
                            )
                    elif tip == "arxivID":
                        md = arxiv_metadata_from_id(ident)
                    else:
                        md = crossref_metadata_from_query(
                            list_of_clean_bibitems[num],
                            threshold=threshold,
                            email=email,
                        )
                    # TODO: can add some NLP for references that don't pass the threshold
                    # here. Alternatively, analyze these references afterwards, pull out
                    # their data from the database
                    citations.append(md)
            elif mode == "xmlAPI":
                dois = []
                arxivIDs = []
                rest = []
                crtCitations = []
                for ident in identifiers:
                    if ident[2] == "DOI":
                        dois.append(ident)
                    elif ident[2] == "arxivID":
                        arxivIDs.append(ident)
                    else:
                        rest.append(ident)
                for num, ident, tip in dois:
                    if check_doi_registration_agency(ident) == "Crossref":
                        md = crossref_metadata_from_doi(ident)
                    else:  # still utilize rest API here
                        md = crossref_metadata_from_query(
                            clean_bibitems[num], threshold=threshold, email=email
                        )
                    crtCitations.append((num, md))
                for num, ident, tip in arxivIDs:
                    md = arxiv_metadata_from_id(ident)
                    crtCitations.append((num, md))
                xmlbibs = [list_of_clean_bibitems[item[0]] for item in rest]
                numbers = [item[0] for item in rest]
                data = []
                bibitemsNum = xmlQueryNum
                if email is None:
                    user_email = "sample.email@gmail.com"
                else:
                    user_email = email
                response_format = "unixsd"  # can be unixref as well
                base_url = "https://doi.crossref.org/servlet/query?usr={usermail}&format={format}&qdata=".format(
                    usermail=user_email, format=response_format
                )
                i = 0
                j = 0
                while i < len(xmlbibs):
                    # Conditional to ensure the final batch of items is correct
                    if i + bibitemsNum < len(xmlbibs):
                        bibs = xmlbibs[i : i + bibitemsNum]
                        xml_query = create_query_batch_xml(bibs)
                    else:
                        bibs = xmlbibs[i:]
                        xml_query = create_query_batch_xml(bibs)
                    print(
                        f"Processing batch number {j} - bibs {i} through {i+len(bibs)}."
                    )

                    try:
                        response = retrieve_rawdata(base_url + xml_query).decode()
                        results = parse_xml_response(response)
                        data += [extract_metadata_from_xml(res) for res in results]
                    except urllib.error.HTTPError as e:  # usually a bad request
                        # don't know how to fix a bad request exception since
                        # I don't know what is causing the bad request
                        # Here we use the crossref REST API
                        for bib in bibs:
                            if xmlUseRESTAPI:
                                data.append(
                                    crossref_metadata_from_query(
                                        bib, threshold=threshold, email=email
                                    )
                                )
                            else:
                                md = create_default_md_dict(FIELDS_TO_STORE)
                                md["status"] = "unresolved"
                                data.append(md)
                    i += bibitemsNum
                    j += 1
                # Add this data to the citations
                for datum, num in zip(data, numbers):
                    crtCitations.append((num, datum))
                # sort the citations by num
                crtCitations.sort(key=lambda elem: elem[0])
                # Only take metadata dictionaries
                crtCitations = [item[1] for item in crtCitations]
                if xmlUseRESTAPI:
                    for i, md in enumerate(crtCitations):
                        if md["status"] == "unresolved":
                            newmd = crossref_metadata_from_query(
                                list_of_clean_bibitems[i],
                                threshold=threshold,
                                email=email
                            )
                            crtCitations[i] = newmd
                citations += crtCitations
            elif mode == "neither":
                for num, ident, tip in identifiers:
                    if tip == "DOI":
                        if check_doi_registration_agency(ident) == "Crossref":
                            md = crossref_metadata_from_doi(ident)
                        else:
                            md = crossref_metadata_from_query(
                                clean_bibitems[num], threshold=threshold, email=email
                            )
                    elif tip == "arxivID":
                        md = arxiv_metadata_from_id(ident)
                    else:
                        md = create_default_md_dict(FIELDS_TO_STORE)
                        md["status"] = "ignored"
                    citations.append(md)
                # TODO: can implement here some sort of NLP to proces the ignored references
                # OR create a completely different script that takes ignored references from storage

    return citations, clean_bibitems, bibitems


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
    hits = []
    for hit in raw_hits:
        for group in hit:
            if group:
                hits.append(group.lower())
    return list(set(hits))


def clean_arxiv_id(id: str) -> str:
    """
    Some references contain faulty arxiv ids. Example: arXiv:math.PR/0003156
    '.PR' part breaks the metadata extraction function. Subcategories can't be
    appended to a category. This function cleans that up.

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
        title
        arxiv_comment
        summary
        id
        arxiv_doi
        updated
        published
        authors
        links
        arxiv_primary_category
        arxiv_journal_ref

    Additionally, we store time_taken which is the amount of time
    taken to get a response from the API

    Args:
        arxivID (str): a valid arXiv ID

    Returns:
        dict: a dictionary with keys being the fields we are
                interested in above
    """
    WHAT_GETS_ASSIGNED_HERE = [
        "status",
        "ref_arxiv_id",
        "DOI",
        "title",
        "abstract",
        "authors",
        "database_name",
        "last_modified_datetime",
        "created_datetime",
        "pdf_link",
        "source_link",
        "arxiv_comment",
        "arxiv_primary_category",
        "type",
        "container",
        "time_taken",
    ]

    SIMPLE_EXTRACT = ["title", "arxiv_comment"]

    base_url = "http://export.arxiv.org/api/query?"

    query = "id_list=%s" % arxivID

    time1 = time.time()
    response = retrieve_rawdata(base_url + query)
    time2 = time.time()

    feed = feedparser.parse(response)
    entry = feed.entries[0]

    metadata = create_default_md_dict(FIELDS_TO_STORE)

    metadata["status"] = "resolved"
    metadata["database_name"] = "arxiv"
    metadata["source_link"] = "https://arxiv.org/abs/" + arxivID
    metadata["type"] = "journal-article"
    # Extract the simple entries
    for item in SIMPLE_EXTRACT:
        try:
            metadata[item] = entry[item]
        except Exception as e:
            print(f"Couldn't get {item}. Exception: {e}")

    try:
        metadata["abstract"] = entry["summary"]
    except Exception as e:
        print(f"Couldn't get summary. Exception {e}.")

    # Extract entries that require some postprocessing
    try:
        metadata["ref_arxiv_id"] = entry.id.split("/abs/")[-1]
    except Exception as e:
        print(f"Couldn't get reference_id. Exception: {e}")

    try:
        metadata["DOI"] = entry["arxiv_doi"]
    except Exception as e:
        print(f"Couldn't get arxiv_doi. Exception {e}")

    try:
        metadata["last_modified_datetime"] = entry["updated"].split("T")[0]
    except:
        print(f"Couldn't get last modified datetime. Exception: {e}")

    try:
        metadata["created_datetime"] = entry["published"].split("T")[0]
    except Exception as e:
        print(f"Couldn't get creation datetime. Exception: {e}")

    try:
        authors = entry["authors"]
        metadata["authors"] = ", ".join([author["name"] for author in authors])
    except Exception as e:
        print(f"Couldn't get authors. Exception: {e}")

    try:
        for link in entry.links:
            if link.rel == "alternate":
                metadata["pdf_link"] = link.href
    except Exception as e:
        print(f"Couldn't get pdf link. Exception: {e}")

    try:
        metadata["arxiv_primary_category"] = entry["arxiv_primary_category"]["term"]
    except Exception as e:
        print(f"Couldn't get arxiv_primary_category. Exception: {e}")

    try:
        metadata["container"] = entry["arxiv_journal_ref"]
    except Exception as e:
        print(f"Couldn't get container. Exception {e}")

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


def crossref_metadata_from_doi(doi: str, email=None) -> dict:
    """
    Provided a valid doi this function will query the CrossRef API
    and parse the returned metadata. The function returns a dictionary
    with the items of interest.

    Metadata we are interested in:
        DOI
        title
        author
        created
        published
        URL
        publisher
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
    WHAT_GETS_ASSIGNED = [
        "status",
        "DOI",
        "title",
        "authors",
        "last_modified_datetime",
        "created_datetime",
        "pdf_link",
        "source_link (we take the publisher)",
        "type",
        "container",
        "time_taken",
    ]

    time1 = time.time()
    if email is not None:
        cr = Crossref(mailto=email)
    else:
        cr = Crossref()

    # Weird bug that needs try: except clause: to get solved
    # For example, the following DOI: 10.2307/2288040
    # When run through the check_doi_registration_agency it returns 'crossref'
    # Yet when queried here a '404 Client Error: Not Found for url:
    # https://api.crossref.org/works/10.2307/2288040
    # And yet https://www.doi.org/10.2307/2288040 happily returns a website
    # No idea what is causing that and how to solve it
    metadata = create_default_md_dict(FIELDS_TO_STORE)
    try:
        work = cr.works(ids=doi)["message"]
        time2 = time.time()
        print(f"Took me {time2-time1:.2f}s to get DOI metadata from Crossref.")

        metadata["status"] = "resolved"
        # Extract entries that require some postprocessing
        try:
            metadata["DOI"] = work["DOI"]
        except Exception as e:
            print(f"Couldn't get DOI. Exception: {e}")

        try:
            # Need [0] because for some reason the title comes back in a list
            metadata["title"] = work["title"][0]
        except Exception as e:
            print(f"Couldn't get title. Exception: {e}")

        try:
            authors = work["author"]
            givenNames = []
            familyNames = []
            for author in authors:
                try:
                    givenNames.append(author["given"])
                except:
                    givenNames.append("")
                try:
                    familyNames.append(author["family"])
                except:
                    familyNames.append("")
            metadata["authors"] = ", ".join(
                [
                    "{} {}".format(first, second)
                    for first, second in zip(givenNames, familyNames)
                ]
            )
        except Exception as e:
            print(f"Couldn't get author. Exception: {e}")

        try:  # work["created"]["date-time"] seems like something most similar to last modified
            # I'm not entirely sure as to what "created" stands for
            # Since there is a different key called "deposited" which is probably
            # the date when the entry was deposited to crossref
            metadata["last_modified_datetime"] = work["created"]["date-time"].split(
                "T"
            )[0]
        except Exception as e:
            print(f"Couldn't get created datetime. Exception: {e}")

        try:
            metadata["created_datetime"] = "-".join(
                [str(item) for item in work["published"]["date-parts"][0]]
            )
        except Exception as e:
            print(f"Couldn't get publishing date. Exception {e}")

        try:
            metadata["pdf_link"] = work["URL"]
        except Exception as e:
            print(f"Couldn't get pdf link. Exception {e}")

        try:
            metadata["source_link"] = work["publisher"]
        except Exception as e:
            print(f"Couldn't get publisher. Exception {e}")

        try:
            metadata["type"] = work["type"]
        except Exception as e:
            print(f"Couldn't get type. Exception {e}")

        try:
            metadata["container"] = work["container-title"][0]
        except Exception as e:
            print(f"Couldn't get container. Exception: {e}")

        metadata["time_taken"] = time2 - time1

    except Exception:
        print(f"Couldn't get metadata from crossref for doi {doi}")
        metadata["status"] = "unresolved"

    return metadata


def crossref_metadata_from_query(bibitem: str, threshold=0, email=None) -> dict:
    """
    This is function that utilizes the habanero module to communicate with the
    crossref API. Given bibitem is processed on the crossref servers which try
    to match a reference to one of the works in their database. Subsequently,
    metadata about the reference can be extracted back.

    One issue is that crossref will always try to match a work to a reference,
    so even if a reference doesn't exist crossref will find something.
    To reject some references tune the threshold paramter.
    By default, it is set to 0 so all references will match to something.
    Out of personal experience, score of about 30 and higher is alright.
    Although, to get a 100% recognition a score of about 60 or higher will
    need to be utilized.

    The function returns a dictionary with the items we are interested in.

    Fields we are interested in:
        DOI,
        title,
        authors,
        created,
        published,
        URL,
        publisher,
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
    WHAT_GETS_ASSIGNED = [
        "status",
        "DOI",
        "title",
        "authors",
        "last_modified_datetime",
        "created_datetime",
        "pdf_link",
        "source_link",
        "type",
        "container",
        "score",
    ]

    time1 = time.time()
    if email is not None:
        cr = Crossref(mailto=email)
    else:
        cr = Crossref()

    metadata = create_default_md_dict(FIELDS_TO_STORE)
    # An error that plagues the Crossref REST API is the ocasional
    # 504 gateway timeout error. Admitedly, this error could be due to
    # faulty firewall settings on my machine, or a miriad of other reasons.
    # In either case, the try except clause is needed so the script
    # keeps running
    try:
        x = cr.works(query_bibliographic=bibitem, limit=1)
        time2 = time.time()
        print(f"It took me {time2-time1:.2f}s to query crossref and get metadata.")

        # if x["message"]["items"]:
        bestItem = x["message"]["items"][0]
        score = bestItem["score"]

        if score > threshold:
            metadata["status"] = "resolved"
            try:
                metadata["DOI"] = bestItem["DOI"]
            except Exception as e:
                print(f"Couldn't get DOI. Exception: {e}")

            try:
                metadata["title"] = bestItem["title"][0]
            except Exception as e:
                print(f"Couldn't get title. Exception: {e}")

            try:
                authors = bestItem["author"]
                givenNames = []
                familyNames = []
                for author in authors:
                    try:
                        givenNames.append(author["given"])
                    except:
                        givenNames.append("")
                    try:
                        familyNames.append(author["family"])
                    except:
                        familyNames.append("")
                metadata["authors"] = ", ".join(
                    [
                        "{} {}".format(first, second)
                        for first, second in zip(givenNames, familyNames)
                    ]
                )
            except Exception as e:
                print(f"Couldn't get author. Exception: {e}")

            try:
                metadata["last_modified_datetime"] = bestItem["created"][
                    "date-time"
                ].split("T")[0]
            except Exception as e:
                print(f"Couldn't get published. Exception: {e}")

            try:
                metadata["created_datetime"] = "-".join(
                    [str(item) for item in bestItem["published"]["date-parts"][0]]
                )
            except Exception as e:
                print(f"Couldn't get publishing date. Exception {e}")

            try:
                metadata["pdf_link"] = bestItem["URL"]
            except Exception as e:
                print(f"Couldn't get pdf link. Exception {e}")

            try:
                metadata["source_link"] = bestItem["publisher"]
            except Exception as e:
                print(f"Couldn't get publisher. Exception {e}")

            try:
                metadata["type"] = bestItem["type"]
            except Exception as e:
                print(f"Couldn't get type. Exception {e}")

            try:
                metadata["container"] = bestItem["container-title"][0]
            except Exception as e:
                print(f"Couldn't get container. Exception: {e}")
            metadata["score"] = bestItem["score"]
        else:
            print(f"Returned score was below the threshold. Marking as unresolved.")
            metadata["status"] = "unresolved"

        metadata["time_taken"] = time2 - time1
    except Exception as e:
        print(f"Couldn't query crossref with the following bibitem: {bibitem}")
        print(f"Got the following error: {e}")
        metadata["status"] = "unresolved"

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

    def remove_from_beggining(openTag, closeTag, string):
        try:
            if string[0] == openTag:
                i = 1
                while string[i] != closeTag:
                    i += 1
                return string[i + 1 :]
            return string
        except:
            print(f"Something went wrong with this string: {string}.")
            return string

    # Many bibtex items start with the local reference name enclosed within the '{}'
    # brackets or some other text within '[]' brackets
    # What we do here is run '{}' removal and then '[]' removal
    # or run '[]' removal and then '{}' removal
    if bibitem[0] == "{":
        bibitem = remove_from_beggining("{", "}", bibitem)
        bibitem = remove_from_beggining("[", "]", bibitem)
    elif bibitem[0] == "[":
        bibitem = remove_from_beggining("[", "]", bibitem)
        bibitem = remove_from_beggining("{", "}", bibitem)

    # Clean up latex items like \em{} etc
    pattern = re.compile(r"\\[A-z]+{")
    bibitem = re.sub(pattern, "", bibitem)
    # Clean up item like \newblock (items which don't utilize '{}')
    pattern = re.compile(r"\\[A-z]+")
    bibitem = re.sub(pattern, "", bibitem)
    # Remove '\n'
    pattern = re.compile(r"\n")
    bibitem = re.sub(pattern, "", bibitem)
    # Clean up simple characters: {}[]
    reduntant_characters = r"{}[]\"'%"
    bibitem = bibitem.translate(
        {ord(char): None for char in reduntant_characters}
    ).strip()
    # Remove the weird ~ symbol
    # I have no idea what it is even used for in bibtex
    # Replace with whitespace though
    bibitem = bibitem.translate({"~": " "})  # for some reason this doesn't work??
    for i in range(len(bibitem)):
        if bibitem[i] == "~":
            bibitem = bibitem[:i] + " " + bibitem[i + 1 :]
    # Remove reduntant white space
    pattern = re.compile(r"\s{2,}")
    bibitem = re.sub(pattern, " ", bibitem)

    return bibitem


def create_query_batch_xml(clean_bibitems: list, email="sample.mail@gmail.com"):

    query_metadata = r"""<?xml version = "1.0" encoding="UTF-8"?>"""
    schema_specs = r"""<query_batch xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns="http://www.crossref.org/qschema/2.0" xsi:schemaLocation="http://www.crossref.org/qschema/2.0 http://www.crossref.org/qschema/crossref_query_input2.0.xsd">"""
    head = f"""<head><email_address>{email}</email_address><doi_batch_id>01032012</doi_batch_id></head>"""
    queries = []
    for i in range(len(clean_bibitems)):
        query = """<query key="q{}" enable-multiple-hits="false" forward-match="false"><unstructured_citation>{}</unstructured_citation></query>""".format(
            i + 1, clean_bibitems[i]
        )
        queries.append(query)
    queries = "".join(queries)
    xml_query = (
        query_metadata
        + schema_specs
        + head
        + "<body>"
        + queries
        + "</body></query_batch>"
    )
    return urllib.parse.quote(xml_query.replace("\n", "").replace("    ", ""))


def parse_xml_response(response):
    root = untangle.parse(response)
    results = root.crossref_result.query_result.body.query
    return results


def extract_metadata_from_xml(singleresult):
    """
    This function extracts the metadata for a response from the XML server.
    Note that the input parameter is called singleresult - it has to be the
    part of the response for a single citation. Moreover, it needs to be
    a single result parsed through the untangle module.

    Unfortunately, the XML API is the most 'result complicated' one.
    Every type of publication has a different XML return scheme and
    a control flow for each type had to be created. Furthermore, there
    can be slight differences in each XML result for the same types
    of publications which then result in the metadata not being extracted.
    For example, sometimes the publication date will be a single
    'Element' instance (class in the untangle package) and other times
    it will be a list of two 'Element' instances, on containing the print
    publication date, the other one containing the online publication date.
    I tried to catch most of these slightly differing schemes but certainly
    there are some that I have missed.

    Args:
        singleresult: single result from the untangle module
                        parsing of the XML response
    """
    md = create_default_md_dict(FIELDS_TO_STORE)
    if singleresult["status"] == "resolved":
        print(f"Reference resolved.")
        # I THINK there should be no problems with these fields
        md["status"] = "resolved"
        md["DOI"] = singleresult.doi.cdata
        md["type"] = singleresult.doi["type"]  # type of publication

        if singleresult.doi["type"] == "journal_article":
            article_data = singleresult.doi_record.crossref.journal.journal_article
            journal_data = singleresult.doi_record.crossref.journal.journal_metadata

            try:
                md["title"] = article_data.titles.title.cdata
            except Exception as e:
                print(f"Couldn't get title. Exception {e}.")

            # authors
            try:
                authors = []
                for item in article_data.contributors.person_name:
                    try:
                        givname = item.given_name.cdata
                    except:
                        givname = ""
                    try:
                        surname = item.surname.cdata
                    except:
                        surname = ""
                    authors.append(givname + " " + surname)
                md["authors"] = ", ".join(authors)
            except Exception as e:
                print(f"Couldn't get authors. Exception {e}")

            # URL
            try:
                md["source_link"] = article_data.doi_data.resource.cdata
            except Exception as e:
                print(f"Couldn't get source link. Exception {e}")

            # publication date
            try:
                date = []
                if isinstance(article_data.publication_date, list):
                    for item in article_data.publication_date[0].children:
                        date.append(item.cdata)
                else:
                    for item in article_data.publication_date.children:
                        date.append(item.cdata)
                md["created_datetime"] = "-".join(date)
            except Exception as e:
                print(f"Couldn't get publication date. Exception {e}")

            # container
            try:
                md["container"] = journal_data.full_title.cdata
            except Exception as e:
                print(f"Couldn't get container. Exception {e}")

        elif singleresult.doi["type"] == "posted_content":
            data = singleresult.doi_record.crossref.posted_content
            # title
            try:
                md["title"] = data.titles.title.cdata
            except Exception as e:
                print(f"Couldn't get title. Exception {e}")

            # authors
            try:
                authors = []
                for item in data.contributors.person_name:
                    try:
                        givname = item.given_name.cdata
                    except:
                        givname = ""
                    try:
                        surname = item.surname.cdata
                    except:
                        surname = ""
                    authors.append(givname + " " + surname)
                md["authors"] = ", ".join(authors)
            except Exception as e:
                print(f"Couldn't get authors. Exception {e}")

            # URL
            try:
                md["source_link"] = data.doi_data.resource.cdata
            except Exception as e:
                print(f"Couldn't get source link. Exception {e}")

            # posted date
            try:
                date = []
                if isinstance(data.posted_date, list):
                    for item in data.posted_date[0].children:
                        date.append(item.cdata)
                else:
                    for item in data.posted_date.children:
                        date.append(item.cdata)
                md["created_datetime"] = "-".join(date)
            except Exception as e:
                print(f"Couldn't get date of posting. Exception {e}")
            # publisher/institution
            # print(data.institution.institution_name.cdata)
        elif singleresult.doi["type"] == "report-paper_title":
            data = singleresult.doi_record.crossref.report_paper.report_paper_metadata
            # title
            try:
                md["title"] = data.titles.title.cdata
            except Exception as e:
                print(f"Couldn't get title. Exception {e}")
            # authors
            try:
                authors = []
                for item in data.contributors.person_name:
                    try:
                        givname = item.given_name.cdata
                    except:
                        givname = ""
                    try:
                        surname = item.surname.cdata
                    except:
                        surname = ""
                    authors.append(givname + " " + surname)
                md["authors"] = ", ".join(authors)
            except Exception as e:
                print(f"Couldn't get authors. Exception {e}")

            # URL
            try:
                md["source_link"] = data.doi_data.resource.cdata
            except Exception as e:
                print(f"Couldn't get source link. Exception {e}")

            # publication date
            try:
                date = []
                if isinstance(data.publication_date, list):
                    for item in data.publication_date[0].children:
                        date.append(item.cdata)
                else:
                    for item in data.publication_date.children:
                        date.append(item.cdata)
                md["created_datetime"] = "-".join(date)
            except Exception as e:
                print(f"Couldn't get publication date. Exception {e}")

            # publisher
            try:
                md["container"] = data.publisher.publisher_name.cdata
            except Exception as e:
                print(f"Couldn't get container. Exception {e}")
        elif singleresult.doi["type"] == "conference_paper":
            paper_data = singleresult.doi_record.crossref.conference.conference_paper
            event_data = singleresult.doi_record.crossref.conference.event_metadata
            proceedings_data = (
                singleresult.doi_record.crossref.conference.proceedings_metadata
            )

            # title
            try:
                md["title"] = paper_data.titles.title.cdata
            except Exception as e:
                print(f"Couldn't get title. Exception {e}")

            # authors
            try:
                authors = []
                for name in paper_data.contributors.person_name:
                    try:
                        givname = name.given_name.cdata
                    except:
                        givname = ""
                    try:
                        surname = name.surname.cdata
                    except:
                        surname = ""
                    authors.append(givname + " " + surname)
                md["authors"] = ", ".join(authors)
            except Exception as e:
                print(f"Couldn't get authors. Exception {e}")

            # publication date
            try:
                date = []
                # sometimes paper_data.publication_date is a list
                # and sometimes a single entry
                dates = paper_data.publication_date
                if isinstance(dates, list):
                    # [0] in the list is usualy publishing date
                    for item in paper_data.publication_date[0].children:
                        date.append(item.cdata)
                else:
                    for item in paper_data.publication_date.children:
                        date.append(item.cdata)
                    md["created_datetime"] = "-".join(date)
            except Exception as e:
                print(f"Couldn't get publication date. Exception {e}")

            # URL
            try:
                md["source_link"] = paper_data.doi_data.resource.cdata
            except Exception as e:
                print(f"Couldn't get source link. Exception {e}")

            # container
            try:
                md["container"] = event_data.conference_name.cdata
            except Exception as e:
                print(f"Couldn't get container. Exception {e}")
            # publisher
            # print(proceedings_data.publisher.publisher_name.cdata)

        elif singleresult.doi["type"] == "book_content":
            content_data = singleresult.doi_record.crossref.book.content_item
            # this one has same fields as the type "book_title, can extract the same thing"
            # I hope this doesn't break with some specific entry
            try:
                book_data = singleresult.doi_record.crossref.book.book_metadata
            except:
                book_data = singleresult.doi_record.crossref.book.book_series_metadata

            # title
            try:
                md["title"] = content_data.titles.title.cdata
            except Exception as e:
                print(f"Couldn't get title. Exception {e}")
            # authors
            try:
                authors = []
                for name in content_data.contributors.person_name:
                    try:
                        givname = name.given_name.cdata
                    except:
                        givname = ""
                    try:
                        surname = name.surname.cdata
                    except:
                        surname = ""
                    authors.append(givname + " " + surname)
                md["authors"] = ", ".join(authors)
            except Exception as e:
                print(f"Couldn't get authors. Exception: {e}")

            # publication date
            try:
                date = []
                data = book_data.publication_date
                if isinstance(data, list):
                    for item in data[0].children:
                        date.append(item.cdata)
                else:
                    for item in book_data.publication_date.children:
                        date.append(item.cdata)
                md["created_datetime"] = "-".join(date)
            except Exception as e:
                print(f"Couldn't get publication date. Exception: {e}")

            # URL
            try:
                md["source_link"] = content_data.doi_data.resource.cdata
            except Exception as e:
                print(f"Couldn't get source link. Exception {e}")

            # publisher
            try:
                md["container"] = book_data.publisher.publisher_name.cdata
            except Exception as e:
                print(f"Couldn't get container. Exception {e}")

        elif singleresult.doi["type"] == "book_title":
            name = singleresult.doi_record.crossref.book.children[0]._name
            data = singleresult.doi_record.crossref.book.get_elements(name=name)[0]

            # title
            try:
                md["title"] = data.titles.title.cdata
            except Exception as e:
                print(f"Couldn't get title. Exception {e}")

            # authors
            try:
                authors = []
                for name in data.contributors.person_name:
                    try:
                        givname = name.given_name.cdata
                    except:
                        givname = ""
                    try:
                        surname = name.surname.cdata
                    except:
                        surname = ""
                    authors.append(givname + " " + surname)
                md["authors"] = ", ".join(authors)
            except Exception as e:
                print(f"Couldn't get authors. Exception {e}")

            # URL
            try:
                md["source_link"] = data.doi_data.resource.cdata
            except Exception as e:
                print(f"Couldn't get source link. Exception {e}")

            # print publication date
            try:
                publication_date = []
                if isinstance(data.publication_date, list):
                    for item in data.publication_date[0].children:
                        publication_date.append(item.cdata)
                else:
                    for item in data.publication_date.children:
                        publication_date.append(item.cdata)
                md["created_datetime"] = "-".join(publication_date)
            except Exception as e:
                print(f"Couldn't get publication date. Exception {e}")
            # online publication date - often isn't contained at all
            # print('-'.join([el.cdata for el in data.publication_date[1].children]))
            # publisher
            try:
                md["container"] = data.publisher.publisher_name.cdata
            except Exception as e:
                print(f"Couldn't get container. Exception {e}")
        else:
            print(f"WARNING: unknown result type - {singleresult.doi['type']}")
        return md
    elif singleresult["status"] == "unresolved":
        md["status"] = "unresolved"
        print("Couldn't resolve reference")
        # print(result.article_title.cdata)
        # print(result.author.cdata)
        # print(result.journal_title.cdata)
        # print(result.year.cdata)
        return md
    else:
        raise Exception(f"Something unexpected happened with {singleresult}.")


time1 = time.time()
create_database(
    "test.db",
    "reference_tree",
    list_of_paper_ids,
    mode="neither",
    email="matejvedak@gmail.com",
    xmlUseRESTAPI=False,
)
time2 = time.time()
print(f"It took me {time2-time1:.2f}s to process a 100 papers.")
print(f"This is equal to {(time2-time1)/3600:.2f} hours.")
print(
    f"At this rate, it would take me {(time2-time1)/3600*20:.2f} hours to process 2000 papers."
)
