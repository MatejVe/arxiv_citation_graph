import sqlite3
import urllib.error
import urllib.request
import urllib.parse
import time
from datetime import datetime


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


def create_query_batch_xml(clean_bibitems: list):
    query_metadata = r"""<?xml version = "1.0" encoding="UTF-8"?>"""
    schema_specs = r"""<query_batch xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns="http://www.crossref.org/qschema/2.0" xsi:schemaLocation="http://www.crossref.org/qschema/2.0 http://www.crossref.org/qschema/crossref_query_input2.0.xsd">"""
    head = r"""<head>
                    <email_address>matejvedak@gmail.com</email_address>
                    <doi_batch_id>01032012</doi_batch_id>
                </head>"""
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
    return urllib.parse.quote(
        xml_query.replace("\n", "").replace("    ", "").replace("&", "")
    )


test_bibitems = [
    "Giovanni Alessandrini and Vincenzo Nesi. Errata corrige. invertible harmonic mappings, beyond Kneser. Annali della Scuola Normale Superiore di Pisa. Classe di scienze, 17(2):815--818, 2017."
    "Danilo Giampiccolo, Bernardo Magnini, Ido Dagan, and Bill Dolan. The Third PASCAL Recognizing Textual Entailment Challenge. ACL-PASCAL Workshop on Textual Entailment and Paraphrasing, 2007."
    "Dominik Stingl, Christian Gross, Leonhard Nobach, Ralf Steinmetz, and David Hausheer. Blocktree: Location-aware decentralized monitoring in mobile ad hoc networks. In IEEE 38th Conf. Local Computer Networks, pages 373--381, 2013."
]
xml_query = create_query_batch_xml(test_bibitems)

user_email = "matejvedak@gmail.com"
response_format = "unixsd"  # can be unixref as well
base_url = "https://doi.crossref.org/servlet/query?usr={usermail}&format={format}&qdata=".format(
    usermail=user_email, format=response_format
)

con = sqlite3.connect("clean.db")
cur = con.cursor()

cur.execute("CREATE TABLE XML_api_speed (time_of_day, return_time, error_code)")

# Request a response for the test_bibitems every every 5 minutes; repeat for 24 hours
# this comes out to a 288 request, each one happening every 5 minutes
for i in range(1440):
    print(f'Query number {i+1} of 1440. {(i+1)/1440 * 100:.2f}%.')
    time1 = time.time()
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    try:
        response = retrieve_rawdata(base_url + xml_query).decode()
        error = "null"
    except urllib.error.HTTPError as e:
        error = str(e.code)
        print(f"Got an HTTP error: {e.code}.")
        print(f"Stated reason: {e.reason}.")
        print(f"Ignoring")
    time2 = time.time()
    deltaT = time2 - time1
    print(f'Time of day is {current_time}, took me {deltaT:.2f}s to get data.')
    print(f'Is there an error? {error}')
    cur.execute(
        "INSERT INTO XML_api_speed VALUES (?, ?, ?)", (current_time, deltaT, error)
    )
    time.sleep(60)
    con.commit()
con.close()
