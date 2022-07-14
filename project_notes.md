# Extracting reference trees from arXiv documents

## Problem description and what we aim to solve

arXiv is a database of publications. Each publication references several other publications, publications that might or might not be within the arXiv itself. Furthermore, there is no standard for writing out references which additionally complicates the problem. In this project, I will work on creating a reliable and robust reference detection software. This programme will primarily be utilized on the following website: [Benty Fields](https://www.benty-fields.com/about). It is a website that helps researchers organize and find the latest publications relevant to their field of research. It supports many feature, such as book clubs and it utilizes arXiv's API to collect information.

## Plan and what tools will be used

The idea of the project is to use the arXiv API to gather data about the papers. Arxiv gives a unique ID to every paper that is submited. Knowing the ID of a paper, it can easily be downloaded using the following query ```http://export.arxiv.org/e-print/paper_id```. After some manipulation, the downloaded files are checked for either a raw .tex file, or a .bib file. Both of these might contain citations withing them. Specifically, the ```\bibitem``` tag can be utilized to find references. ArXiv ids are checked for first, as they are a very reliable identification. We will be implementing our own arXiv id finder but a good script can be found here [arxiv-public-datasets/arxiv_public_data/regex_arxiv.py](https://github.com/mattbierbaum/arxiv-public-datasets/blob/master/arxiv_public_data/regex_arxiv.py). Second, DOIs for each reference are found. DOI (digital object identifier) is perhaps the best identificator we can find. If neither of these two identificators are present, some other methods must be utilized. We can try extracting author names and the title of the paper and try searching the arXiv archive itself. Furthermore, other online resources can be utilized, such as [crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).

Unfortunatelly, such firm methods of referencing are found in a minority of references. When utilizing the online DOI regex, and with the addition of STRICT_ARXIV_ID and
FLEXIBLE_ARXIV_ID, in a test set of a 100 papers only 13.85% of references are found (total number of references is 4555 and we find 631 reference).
The previous arxiv id regex (in addition to the doi regex) found 16.01%
of the references in the test set (found references 677, total 4227 mismatch?? -
find cause). However, some of these references are a false positive and I believe
that the strong arxiv checking is a better way of identifing references.

This is why we have to turn our attention to references that contain neither. Most popular methods for
understanding such references involve machine learning and natural language
processing. To that end, we have found a great papaer that describes in detail
the methods utilized in such parsing: [Identify and extract entities from
bibliography references in a free text](https://essay.utwente.nl/73817/1/chenet_MA_EEMCS.pdf).

Luckily, crossref offers automatic parsing of pure text references. Details can be found online (PUT A LINK HERE!). This automatic parsing can be accesed through their API as well. The problem is, it is optimized for pure text inputs, while we are getting access to latex code at the moment. How it affects performance remains to be seen. Furthermore, querying the API is time intensive: each reference query takes between 1s - 5s, significantly increasing the running time.

One thing we were interested in during this project was how many references do contain arxiv ids. The hypothesis was that as the years went by and arxiv ids became better established among the scientific community the ratio of references that contain an arxiv id to all the references in a paper would grow. To that end, we decided that we should analyse 50 arxiv papers for each year of its existance (1992 - today). Grabbing the papers proved to be a significant challenge of its own. Arxiv API doesn't have a selection by year query so the best we could do was utilize some other selectors and keep grabbing papers until we get enough papers for each year. Naturally, just grabbing all the papers would take forever - there are around 2 000 000 papers on arxiv (Check this). For this reason, we decided to search only within certain categories, categories which contain a more reasonable amount of papers. Categories of experimental high energy particle physics & general relativity and quantum cosmology were chosen. When sending a GET request to the arxiv servers, a special parameter was provided that allowed us to get papers in ascending (or descending) order by the date of publishing. There still was an issue of having to go through all the papers in a category. Arxiv servers didn't help in this matter, as they would sometimes 'lock' the requests out and would stop returning any data whatsoever. Other times, randomly they would return an empty xml but continue providing future requests. Initially, the request grabbed a 1000 entries at once from the servers and this proved to be not the best method. If the response was empty a full year of entries would be skippend. In addition, the servers were not too happy with the size of this request and would frequently stop returning any information. Settting the number of instances grabbed in a single request to a 100 helped to calm down the servers, albeit at a much longer total time of grabbing the papers.

The results were pretty much what was expected. The reference percentage increases through the years as the arXiv ids became more standardized. However, maximum average percentage is around 50% as there are a lot of papers that aren't in the arXiv database. Furthermore, it looks like authors either put an arXiv id in almost every reference they have (and for which there exists and arXiv paper) or almost nowhere at all. The median and Q1 and Q3 data seems to support this.
![Statistical data for arXiv id percentage within arXiv papers throughout the years](/arxivIDs_percentage_analysis/arxiv_id_percentage_median_grqc.png)

Having all the pieces in place, a robust metadata extraction system was constructed. If we can find an arXiv id within a reference metadata is extracted from the arXiv API. If we find a DOI or there is neither a DOI nor arXiv id crossref API is queried for metadata extraction. Metadata fields we are interested in are split into three groups: common metadata, arXiv specific and CrossRef specific.
Common metadata:

* arxiv_id/DOI
* title
* authors
* URL (link)
* date of publishing

ArXiv specific metadata:

* summary (usually the abstract)
* arxiv_comment (often contains information on where the paper was published)
* arxiv_primary_category

CrossRef specific metadata:

* publication type (book, paper, ...)
* container (where it was published)
* score (only applies to entries that we didn't find a DOI for, specifies how 'certain' CrossRef is in the match)

Some other data was extracted which was used mostly for performance testing:

* length of the pure reference
* time taken to extract metadata

Extracted metadata was stored in a database. To start with, we utilized SQLite. SQLite is a simple, robust and quick databse usually used for small entreprise products. All of the above metadata fields were stored for each reference. It took about 3.5 hours to process a 100 papers. Unfortunatelly, this is unnaceptable considering there are about 2000 papers released daily on arXiv.

The main speed bottleneck is the crossref API query. Depending on the reference it can take up to 15 seconds to get a response from the server. The simplest and perhaps the easiest idea to improve this performance is to query references in bulk instead of one-by-one. Unfortunatelly, CrossRef's REST API doesn't provide this capability so we started looking into CrossRef's XML API.

## Code description

Note: lots of bad referencing within the files. Perhaps arXiv files could be found by searching up author's names within arXiv's files. Supplemented by additional info (say publication year or whatever else can be found) it might prove to be reliable enough to supplement arXiv ID matching or DOI matching.
A great deal of references won't be in arXiv at all, mostly because they were published before arXiv was created. See if there is any use in cross-checking author names or is it better to only focus on arXiv ids and DOIs.

[crossref blog on reference matching](https://www.crossref.org/categories/reference-matching/#:~:text=Matching%20(or%20resolving)%20bibliographic%20references,indexes%2C%20impact%20factors%2C%20etc)
