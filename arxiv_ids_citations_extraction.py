import json
import matplotlib.pyplot as plt
from arxiv_regex import *

import gzip
import os
import re
import shutil
import tarfile
import time
import urllib.error
import urllib.request
import chardet
SOURCE_FOLDER = 'dummy'

def get_file(paper_id):
    """
    Returns a list of files which could contain citation information.
    We use all .tex and .bbl files
    """
    url = "http://export.arxiv.org/e-print/%s" % paper_id
    filename = SOURCE_FOLDER + '/%s' % paper_id.replace(".", "_").replace("/", "_")
    rawdata = retrieve_rawdata(url)
    if rawdata is not None:
        unpack_rawdata(rawdata, filename)

        # get all files
        all_files = []
        for path, subdirs, files in os.walk(filename + '.folder_dummy'):
            for name in files:
                all_files.append(os.path.join(path, name))
        # get all .bbl files
        list_of_files = [f for f in all_files if (f.endswith('.bbl') or f.endswith('.tex'))]
        print("list_of_files = ", list_of_files)
        return filename, list_of_files
    else:
        return filename, []

def retrieve_rawdata(url):
    """
    This function gets the data from arxiv and returns the
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
    target_folder = filename + '.folder_dummy'
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)

    if rawdata[0:2] == b'%P':
        print('Seems to be a doc file, so far no processing of doc files has been implemented')
    else:
        with open(filename + '.tar', "wb") as file:
            file.write(rawdata)

        try:
            tar = tarfile.open(filename + '.tar')
            tar.extractall(path=target_folder)
            tar.close()
        except:
            data = gzip.decompress(rawdata)
            file_ = open(target_folder + '/dummy.tex', 'wb')
            file_.write(data)
            file_.close()
    return

def get_data_string(filename):
    """
    Here we read the data file and decode the byte string
    """
    try:
        with open(filename, 'rb') as f:
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
            contents = contents.decode('utf-8', 'ignore')
        else:
            # Even though we tried to determine the encoding above,
            # it still happens that we get errors here
            contents = contents.decode(encoding, 'ignore')
        return contents

def check_for_arxiv_id_strict(citation):
    """
    Strict regex for finding arxiv ids. This will essentially only match if the 
    format of the arxiv id is exactly as specified https://arxiv.org/help/arxiv_identifier
    Seems to have no false positives but on the other hand it doesn't detect a lot of
    arxiv ids
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

def check_for_arxiv_id_flexible(citation):
    """
    Flexible regex for finding arxiv ids. As specified in the arxiv_regex.py:
    this regex essentially accepts anything that looks like an arxiv id and has
    the slightest smell of being one as well. that is, if it is an id and
    mentions anything about the arxiv before hand, then it is an id.
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

def get_proportion_of_arxiv_ids(list_of_files):
    """
    This function starts with a list of files which could contain
    citation information and returns a list of arxiv_ids
    Args:
        list_of_files (_type_): _description_
    """
    total_citations = 0
    strict_ids = 0
    flexible_ids = 0

    for filename in list_of_files:
        contents = get_data_string(filename)
        # Check whether we have citation information in this file
        if contents.find(r'\bibitem') > -1:
            # remove the text before the first appearance of '\bibitem'
            # and after the appearance of '\end{thebibliography}
            first_bibitem = contents.find(r'\bibitem')
            bibliography_end = contents.find(r'\end{thebibliography}')
            contents = contents[first_bibitem:bibliography_end]
            # split by bibitem to get a list of citations
            list_of_bibitems = contents.split(r'\bibitem')
            # Filter the list of empty '' tags
            list_of_bibitems = list(filter(lambda item: item, list_of_bibitems))
            # Strip the empty spaces
            list_of_bibitems = [item.strip() for item in list_of_bibitems]

            total_citations += len(list_of_bibitems)

            for i, bibitem in enumerate(list_of_bibitems):
                strict_arxiv_id = check_for_arxiv_id_strict(bibitem)
                if strict_arxiv_id: strict_ids += 1

                flexible_arxiv_id = check_for_arxiv_id_flexible(bibitem)
                if flexible_arxiv_id and not strict_arxiv_id: flexible_ids += 1
            
            print(f'Total number of references is {total_citations}.')
            print(f'There are {strict_ids} strict arxiv ids.')
            print(f'There are {flexible_ids} flexible arxiv ids.')

    if total_citations != 0:
        return (strict_ids, flexible_ids, total_citations)
    else:
        return None



with open("arxiv_ids_by_years_grqc.json", "r") as datafile:
    arxiv_ids = json.load(datafile)

import statistics as stats

citations_percentage = []

for year in arxiv_ids:
    year_data = []
    for i, paper_id in enumerate(arxiv_ids[year]):
        print(f'process paper {paper_id}, {i}')
        filename, list_of_files = get_file(paper_id)
        if list_of_files:
            outData = get_proportion_of_arxiv_ids(list_of_files)
            if outData is not None: # Check if any references were found at all
                s, f, t = outData # strict arxiv ids, flexible ids, total citations
                year_data.append((s+f)/t)
        
        if os.path.exists(filename + '.tar'):
            print("Delete tar file")
            os.remove(filename + '.tar')
        if os.path.exists(filename + '.folder_dummy'):
            print("Delete folder %s.folder_dummy" % filename)
            shutil.rmtree(filename + '.folder_dummy')
    # Get mean and sample variance
    if year_data:
        citations_percentage.append((stats.mean(year_data), stats.stdev(year_data)))

years = [int(year) for year in arxiv_ids.keys()]
percentages = [item[0] for item in citations_percentage]
err = [item[1] for item in citations_percentage]

with open('arxiv_id_percentage_grqc', 'w') as datafile:
    for year, perc, er in zip(years, percentages, err):
        datafile.write(f'{year} {perc} {er}\n')