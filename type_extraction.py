import sqlite3
import urllib.error
import urllib.request
import urllib.parse
import time
import untangle

import matplotlib.pyplot as plt

con = sqlite3.connect("clean.db")
cur = con.cursor()

bibitems = []
for row in cur.execute(
    'SELECT clean_bibitem FROM reference_tree WHERE id_type = "DOI"'
):
    bibitems.append(row[0])
con.close()


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


user_email = "matejvedak@gmail.com"
response_format = "unixsd"  # can be unixref as well
base_url = "https://doi.crossref.org/servlet/query?usr={usermail}&format={format}&qdata=".format(
    usermail=user_email, format=response_format
)


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


startTime = time.time()
unique_types = []
unique_bibitems = []
lens = []
times = []
resolvedNum = 0
unresolvedNum = 0
deniedBibitems = []

# for bibitemsNum = 5 speed of 2.74s per ref
i = 0
bibitemsNum = 10
j = 0
while i < len(bibitems) - bibitemsNum:
    print(f"Processing batch number {j} - bibitems {i} through {i+bibitemsNum}.")
    bibs = bibitems[i : i + bibitemsNum]
    print(f"Total length of queried bibitems is {sum([len(bib) for bib in bibs])}.")
    xml_query = create_query_batch_xml(bibs)
    time1 = time.time()
    try:
        response = retrieve_rawdata(base_url + xml_query).decode()
        time2 = time.time()
        lens.append(sum([len(bib) for bib in bibs]))
        times.append(time2 - time1)
        print(f"Took me {time2-time1:.2f}s to retrieve data from the server.")
        root = untangle.parse(response)
        results = root.crossref_result.query_result.body.query
        for k, result in enumerate(results):
            if result["status"] == "resolved":
                tip = result.doi["type"]
                if tip not in unique_types:
                    unique_types.append(tip)
                    unique_bibitems.append(bibs[k])
                resolvedNum += 1
            elif result["status"] == "unresolved":
                unresolvedNum += 1
        i += bibitemsNum
    except urllib.error.HTTPError as e:
        # sleep_sec = int(e.hdrs.get("retry-after", 30))
        print("WARNING: Got %d. Moving on." % (e.code))
        deniedBibitems += bibs
        i += bibitemsNum
        bibitemsNum -= 1

    if bibitemsNum == 0:
        print(
            f"WARNING: kept getting 504 responses even for queries of 1 bibitem. Breaking"
        )
        break

    j += 1
endTime = time.time()

print(
    f"Sucessfully resolved {resolvedNum} references, and I was unsucessful {unresolvedNum} times."
)
for tip, bib in zip(unique_types, unique_bibitems):
    print(f"Found type {tip} for {bib}.")
print(
    f"It took me in total {endTime-startTime:.2f}s, {(endTime-startTime)/60:.2f} mins"
)
print(
    f"{(endTime-startTime)/3600:.2f} hours to retrieve data for {len(bibitems) - len(deniedBibitems)} bibitems."
)
print(
    f"This is a speed of {(endTime-startTime)/(len(bibitems))} s per reference, taking in mind that {len(deniedBibitems)} have not been processed."
)

plt.scatter(lens, times)
plt.xlabel("Bibitems length")
plt.ylabel("Time [s]")
plt.savefig("len_vs_time")
plt.close()
