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
    return urllib.parse.quote(xml_query.replace("\n", "").replace("    ", "").replace("&", ""))


# TODO: lots of these fields might not work a 100% because a list comes in the way
# check for list an extract that way
# TODO: find a common blueprint for all this
def parse_xml_response(response):
    root = untangle.parse(response)
    results = root.crossref_result.query_result.body.query
    for i, result in enumerate(results):
        if result["status"] == "resolved":
            print(result.doi.cdata)  # DOI
            print(result.doi["type"])  # type of publication
            # also possible 'book_content'
            if (result.doi["type"] == "journal_article"):
                article_data = result.doi_record.crossref.journal.journal_article
                journal_data = result.doi_record.crossref.journal.journal_metadata
                #title
                print(article_data.titles.title.cdata)
                #authors
                authors = []
                for item in article_data.contributors.person_name:
                    authors.append(item.given_name.cdata + ' ' + item.surname.cdata)
                print(', '.join(authors))
                # URL
                print(article_data.doi_data.resource.cdata)
                # publication date
                date = []
                if isinstance(article_data.publication_date, list):
                    for item in article_data.publication_date[0].children:
                        date.append(item.cdata)
                else:
                    for item in article_data.publication_date.children:
                        date.append(item.cdata)
                print('-'.join(date))
                # container
                print(journal_data.full_title.cdata)
            elif result.doi["type"] == "posted_content":
                data = result.doi_record.crossref.posted_content
                # title
                print(data.titles.title.cdata)
                # authors
                authors = []
                for item in data.contributors.person_name:
                    authors.append(item.given_name.cdata + ' ' + item.surname.cdata)
                print(', '.join(authors))
                # URL
                print(data.doi_data.resource.cdata)
                # posted date
                date = []
                for item in data.posted_date.children:
                    date.append(item.cdata)
                print('-'.join(date))
                # publisher/institution
                print(data.institution.institution_name.cdata)
            elif result.doi["type"] == "report-paper_title":
                data = result.doi_record.crossref.report_paper.report_paper_metadata
                #title
                print(data.titles.title.cdata)
                # authors
                print(', '.join([name.given_name.cdata+' '+name.surname.cdata for name in data.contributors.person_name]))
                # URL
                print(data.doi_data.resource.cdata)
                # publication date
                date = []
                for item in data.publication_date.children:
                    date.append(item.cdata)
                print('-'.join(date))
                # publisher
                print(data.publisher.publisher_name.cdata)
            elif result.doi["type"] == "conference_paper":
                paper_data = result.doi_record.crossref.conference.conference_paper
                event_data = result.doi_record.crossref.conference.event_metadata
                proceedings_data = result.doi_record.crossref.conference.proceedings_metadata

                # title
                print(paper_data.titles.title.cdata)
                #authors
                authors = []
                for name in paper_data.contributors.person_name:
                    name = name.given_name.cdata + ' ' + name.surname.cdata
                    authors.append(name)
                print(', '.join(authors))
                # publication date
                date = []
                for item in paper_data.publication_date.children:
                    date.append(item.cdata)
                print('-'.join(date))
                # URL
                print(paper_data.doi_data.resource.cdata)
                # container
                print(event_data.conference_name.cdata)
                # publisher
                print(proceedings_data.publisher.publisher_name.cdata)
            elif result.doi["type"] == "book_content":
                content_data = result.doi_record.crossref.book.content_item
                # this one has same fields as the type "book_title, can extract the same thing"
                try:
                    book_data = result.doi_record.crossref.book.book_metadata
                except:
                    book_data = result.doi_record.crossref.book.book_series_metadata

                # title
                print(content_data.titles.title.cdata)
                # authors
                authors = []
                for name in content_data.contributors.person_name:
                    name = name.given_name.cdata + ' ' + name.surname.cdata
                    authors.append(name)
                print(', '.join(authors))
                # publication date
                date = []
                for item in book_data.publication_date.children:
                    date.append(item.cdata)
                print('-'.join(date))
                # URL
                print(content_data.doi_data.resource.cdata)
                # publisher
                print(book_data.publisher.publisher_name.cdata)
            elif result.doi["type"] == "book_title":
                name = result.doi_record.crossref.book.children[0]._name
                data = result.doi_record.crossref.book.get_elements(name=name)[0]
                # title
                print(data.titles.title.cdata)
                # authors
                authors = []
                for name in data.contributors.person_name:
                    name = name.given_name.cdata + ' ' + name.surname.cdata
                    authors.append(name)
                print(', '.join(authors))
                # URL
                print(data.doi_data.resource.cdata)
                # print publication date
                publication_date = []
                if isinstance(data.publication_date, list):
                    # TODO: improve this to grab the actual publication date
                    # not just the first date (although this is usualy the publication date)
                    for item in data.publication_date[0].children:
                        publication_date.append(item.cdata)
                else:
                    for item in data.publication_date.children:
                        publication_date.append(item.cdata)
                print('-'.join(publication_date))
                # online publication date - often isn't contained at all
                # print('-'.join([el.cdata for el in data.publication_date[1].children]))
                # publisher
                print(data.publisher.publisher_name.cdata)
            else:
                print("WARNING: unknown result type")
        elif result["status"] == "unresolved":
            print("Couldnt resolve reference")
            #print(result.article_title.cdata)
            #print(result.author.cdata)
            #print(result.journal_title.cdata)
            #print(result.year.cdata)
        else:
            raise Exception(f"Something unexpected happened with {references[i]}.")

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
    "Luca Bertinetto, Jack Valmadre, Jo~ao~F Henriques, Andrea Vedaldi, and Philip H.~S. Torr. Fully-convolutional siamese networks for object tracking. In the European Conference on Computer Vision (ECCV) Workshops, 2016.",
    "Berndt, J., Console, S. and Olmos, C., Submanifoldsand holonomy, Research Notes in Mathematics 434, Chapman &Hall/CRC, 2003.",
]
xml_query = create_query_batch_xml(references)

response = retrieve_rawdata(base_url + xml_query).decode()

parse_xml_response(response)

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
