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
    return urllib.parse.quote(xml_query.replace("\n", "").replace("    ", ""))


xml_query = r"""
<?xml version = "1.0" encoding="UTF-8"?>
<query_batch xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns="http://www.crossref.org/qschema/2.0" xsi:schemaLocation="http://www.crossref.org/qschema/2.0 http://www.crossref.org/qschema/crossref_query_input2.0.xsd">
    <head>
        <email_address>matejvedak@gmail.com</email_address>
        <doi_batch_id>01032012</doi_batch_id>
    </head>
    <body>
        <query key="q2" enable-multiple-hits="false" forward-match="false">
            <unstructured_citation>M.L. Goldberger and K.M. Watson, Collision Theory , John Wiley and Sons, New York (1964).</unstructured_citation>
        </query>
    </body>
</query_batch>"""

# xml_query = urllib.parse.quote(xml_query.replace("\n", "").replace("    ", ""))
# xml_query = create_query_batch_xml(["Hungate, B. A. (2012). Ecosystem services: Valuing ecosystems for climate. Nature Climate Change, 2(3), 151-152.", "Boucher RC (2004) New concepts of the pathogenesis of cystic fibrosis lung disease. Eur Resp J 23: 146–158."])
# TODO: for some reason some '&' break the query. Although, the query seems to work OK with just removing the '&' character
# The manual says encode the '&' character as '%26' but that doesn't seem to work
references = [
    "Bretthorst, G.~L. 1988, Bayesian Spectrum Analysis and Parameter Estimation, ed. Berger,~J.,~Fienberg,~S.,~Gani,~J.,Krickenberg,~K., Singer, B. (Springer-Verlag, New York)",
    "Hungate, B. A. (2012). Ecosystem services: Valuing ecosystems for climate. Nature Climate Change, 2(3), 151-152.",
]
xml_query = create_query_batch_xml(references)

response = retrieve_rawdata(base_url + xml_query).decode()
# print(response)
# response = response.replace(" ", "").replace("\n", "").replace("\r", "")
# print(response)
root = untangle.parse(response)
results = root.crossref_result.query_result.body.query

"""
Having processed all the bibitems here are the found types and sample bibitem
book_title: Alderman, H. (1998). Social assistance in Albania : decentralization and targeted transfers. Living Sandards Measurement Survey Working Paper No. 134.
journal_article: Arnold, D., Brandle, T., and Goerke, L. (2014). Sickness Absence and Works Councils: Evidence from German Individual and Linked Employer-Employee Data. SOEPpapers on Multidisciplinary Panel Data Research at DIW Berlin No. 691.
book_content: Griliches, Z. and Mairesse, J. (1998). Production Functions: The Search for Identification. In Strom, S., editor, Econometrics and Economic Theory in the 20th Century, pages 169--203.
conference_paper: Conoscenti, M., Vetro, A. and De Martin, J. C., ``Blockchain for the Internet of Things: A systematic literature review, IEEE/ACS 13th International Conference on Computer Systems and Applications, pp. 1-6, November 2016.
report-paper_title: B.~Vioreanu, Spectra of Multiplication Operators as a Numerical Tool, Yale University, 2012.
posted_content: M.~Sesia, E.~Katsevich, S.~Bates, E.~Cand, and C.~Sabatti. Multi-resolution localization of causal variants across the genome. bioRxiv (2019).

2/3 of bibitems get sucessfully resolved, a third is left unresolved
"""

if results[0]["status"] == "resolved":
    print(results[0].doi.cdata)  # DOI
    print(results[0].doi["type"])  # type of publication
    # also possible 'book_content'
    if (
        results[0].doi["type"] == "journal-article"
        or results[0].doi["type"] == "journal_article"
    ):
        print(
            results[0].doi_record.crossref.journal.journal_article.titles.title.cdata
        )  # title
        print(
            results[0].doi_record.crossref.journal.journal_article.contributors
        )  # authors
        # The following can also be collection.item[0].resource.cdata
        print(
            results[0]
            .doi_record.crossref.journal.journal_article.doi_data.collection[0]
            .item.resource.cdata
        )  # URL
        # might not be a list, might just be publication_date.year.cdata
        print(
            results[0]
            .doi_record.crossref.journal.journal_article.publication_date[0]
            .year.cdata
        )  # published
        print(
            results[0].doi_record.crossref.journal.journal_metadata.full_title.cdata
        )  # Container name
    elif results[0].doi["type"] == "book_title":
        print(
            results[0].doi_record.crossref.book.book_series_metadata.titles.title.cdata
        )  # title
        print(
            results[0].doi_record.crossref.book.book_series_metadata.contributors
        )  # authors
        print(
            results[
                0
            ].doi_record.crossref.book.book_series_metadata.doi_data.resource.cdata
        )  # URL
        # TODO: check this publication data, might be a list or it might be a single entry publication_date.year.cdata
        print(
            results[0]
            .doi_record.crossref.book.book_series_metadata.publication_date[0]
            .year.cdata
        )  # published
        print(
            results[
                0
            ].doi_record.crossref.book.book_series_metadata.series_metadata.titles.title.cdata
        )  # container name
elif results[0]["status"] == "unresolved":
    print(results[0].article_title.cdata)
    print(results[0].author.cdata)
    print(results[0].journal_title.cdata)
    print(results[0].year.cdata)
else:
    raise Exception(f"Something unexpected happened with {references[0]}.")
