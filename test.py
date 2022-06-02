import urllib.request
import time
import os
import gzip
import tarfile

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

SOURCE_FOLDER = 'dummy'
url = "http://export.arxiv.org/e-print/1902.00678"
filename = SOURCE_FOLDER + '/1902_00678'
rawdata = retrieve_rawdata(url)
if rawdata is not None:
    unpack_rawdata(rawdata, filename)

    all_files = []
    for path, subdirs, files in os.walk(filename + '.folder_dummy'):
        for name in files:
            all_files.append(os.path.join(path, name))
    list_of_files = [f for f in all_files if (f.endswith('.bbl') or f.endswith('.tex'))]
    print("list_of_files = ", list_of_files)