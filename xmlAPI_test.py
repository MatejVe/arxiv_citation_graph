import urllib.error
import urllib.request
import urllib.parse
import time
import untangle


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


# URL encodings
replace_dict = {"<": "%3C", " ": "%20", '"': "%22", ">": "%3E"}

user_email = "matejvedak@gmail.com"
response_format = "unixsd"  # can be unixref as well
base_url = "https://doi.crossref.org/servlet/query?usr={usermail}&format={format}&qdata=".format(
    usermail=user_email, format=response_format
)

xml_query = r"""
<?xml version = "1.0" encoding="UTF-8"?>
<query_batch xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns="http://www.crossref.org/qschema/2.0" xsi:schemaLocation="http://www.crossref.org/qschema/2.0 http://www.crossref.org/qschema/crossref_query_input2.0.xsd">
    <head>
        <email_address>matejvedak@gmail.com</email_address>
        <doi_batch_id>01032012</doi_batch_id>
    </head>
    <body>
        <query key="q2" enable-multiple-hits="true">
            <unstructured_citation>M.L. Goldberger and K.M. Watson, Collision Theory , John Wiley and Sons, New York (1964).</unstructured_citation>
        </query>
    </body>
</query_batch>"""

xml_query = urllib.parse.quote(xml_query.replace("\n", "").replace("    ", ""))

test_query = r"""https://doi.crossref.org/servlet/query?usr=email@address.com&format=unixsd&qdata=%3C?xml%20version%20=%20%221.0%22%20encoding=%22UTF-8%22?%3E%20%3Cquery_batch%20xmlns:xsi=%22http://www.w3.org/2001/XMLSchema-instance%22%20version=%222.0%22%20xmlns=%22http://www.crossref.org/qschema/2.0%22%20%20xsi:schemaLocation=%22http://www.crossref.org/qschema/2.0%20http://www.crossref.org/qschema/crossref_query_input2.0.xsd%22%3E%3Chead%3E%3Cemail_address%3Esupport@crossref.org%3C/email_address%3E%3Cdoi_batch_id%3EABC_123_fff%3C/doi_batch_id%3E%20%3C/head%3E%20%3Cbody%3E%20%3Cquery%20key=%221178517%22%20enable-multiple-hits=%22false%22%20forward-match=%22false%22%3E%3Cissn%20match=%22optional%22%3E15360075%3C/issn%3E%3Cjournal_title%20match=%22exact%22%3EAmerican%20Journal%20of%20Bioethics%3C/journal_title%3E%3Cauthor%20match=%22fuzzy%22%20search-all-authors=%22false%22%3EAgich%3C/author%3E%3Cvolume%20match=%22fuzzy%22%3E1%3C/volume%3E%3Cissue%3E1%3C/issue%3E%3Cfirst_page%3E50%3C/first_page%3E%3Cyear%3E2001%3C/year%3E%3Carticle_title%3EThe%20Salience%20of%20Narrative%20for%20Bioethics%3C/article_title%3E%3C/query%3E%3C/body%3E%3C/query_batch%3E"""

response = retrieve_rawdata(base_url + xml_query).decode()
print(response)
# response = response.replace(" ", "").replace("\n", "").replace("\r", "")
# print(response)
root = untangle.parse(response)
