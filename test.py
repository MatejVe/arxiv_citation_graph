import urllib.request
import time
import os
import gzip
import tarfile
import chardet
import re

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

def get_citations(list_of_files):
    """
    This function starts with a list of files which could contain
    citation information and returns a list of arxiv_ids
    """
    citations = []
    for filename in list_of_files:
        contents = get_data_string(filename)
        # Check whether we have citation information in this file
        if contents.find(r'\bibitem') > -1:
            # remove the text before the first appearance of '\bibitem'
            contents = contents[contents.find(r'\bibitem'):]
            # split by bibitem to get a list of citations
            list_of_bibitems = contents.split(r'\bibitem')
            for bibitem in list_of_bibitems:
                # for each citation check whether there is an arxiv_id tag
                results_arxiv_id = check_for_arxiv_id(bibitem)
                # for each citation check whether there is an doi tag
                results_doi = check_for_doi(bibitem)
                # -> Are there alternatives to the doi and arxiv_id searches above?

                #results_common = check_results(results_arxiv_id, results_doi)
                #if results_common:
                citations.append(results_arxiv_id)
    print("citations = ", citations)
    return citations

def check_for_arxiv_id(citation):
    """
    This function returns arxiv ids using regular expressions.
    In many cases this regular expression selects false patterns.
    -> Can you find a better regular expression?
    """
    pattern = re.compile('(\d{4}.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?\/\d{7})(v\d+)?', re.IGNORECASE)
    return list(set([hit[0].lower() for hit in re.findall(pattern, citation)]))

def check_for_doi(citation):
    """
    This function returns dois using regular expressions. So far I haven't seen
    false positive with this selection.
    Note that while this regular expression matches most dois, it does not match
    all of them. For more details see
    https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    """
    pattern = re.compile('10.\\d{4,9}/[-._;()/:a-z0-9A-Z]+', re.IGNORECASE)
    return list(set(re.findall(pattern, citation)))

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

SOURCE_FOLDER = 'dummy'

list_of_test_ids = ['1902.00678', '1009.3615', '2010.07848', '1903.12466', '1711.07930', '1103.5007',
                     '0712.2987', '1904.11042', '1207.4206', '1208.3840', '1703.05187', 'math/0103136', '1403.2332',
                     'astro-ph/9807138', '1909.03570', '1005.2643', 'hep-th/9211122', '1609.06992', '1912.10120',
                     '1502.04754']

for id in list_of_test_ids:
    url = "http://export.arxiv.org/e-print/%s"%id
    filename = SOURCE_FOLDER + '/%s'%id
    rawdata = retrieve_rawdata(url)
    if rawdata is not None:
        unpack_rawdata(rawdata, filename)

        all_files = []
        for path, subdirs, files in os.walk(filename + '.folder_dummy'):
            for name in files:
                all_files.append(os.path.join(path, name))
        list_of_files = [f for f in all_files if (f.endswith('.bbl') or f.endswith('.tex'))]
        print("list_of_files = ", list_of_files)

get_citations(list_of_files)