# Extracting reference trees from arXiv documents

## Problem description and what we aim to solve

arXiv is a database of publications. Each publication references several other publications, publications that might or might not be within the arXiv itself. Furthermore, there is no standard for writing out references which additionally complicates the problem. In this project, I will work on creating a reliable and robust reference detection software. This programme will primarily be utilized on the following website: [Benty Fields](https://www.benty-fields.com/about). It is a website that helps researchers organize and find the latest publications relevant to their field of research. It supports many feature, such as book clubs and it utilizes arXiv's API to collect information.

## Plan and what tools will be used

The idea of the project is to use the arXiv API to gather data about the papers. Arxiv gives a unique ID to every paper that is submited. Knowing the ID of a paper, it can easily be downloaded using the following query ```http://export.arxiv.org/e-print/paper_id```. After some manipulation, the downloaded files are checked for either a raw .tex file, or a .bib file. Both of these might contain citations withing them. Specifically, the ```\bibitem``` tag can be utilized to find references. ArXiv ids are checked for first, as they are a very reliable identification. We will be implementing our own arXiv id finder but a good script can be found here [arxiv-public-datasets/arxiv_public_data/regex_arxiv.py](https://github.com/mattbierbaum/arxiv-public-datasets/blob/master/arxiv_public_data/regex_arxiv.py). Second, DOIs for each reference are found. DOI (digital object identifier) is perhaps the best identificator we can find. If neither of these two identificators are present, some other methods must be utilized. We can try extracting author names and the title of the paper and try searching the arXiv archive itself. Furthermore, other online resources can be utilized, such as [crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).

## Code description

Note: lots of bad referencing within the files. Perhaps arXiv files could be found by searching up author's names within arXiv's files. Supplemented by additional info (say publication year or whatever else can be found) it might prove to be reliable enough to supplement arXiv ID matching or DOI matching.
A great deal of references won't be in arXiv at all, mostly because they were published before arXiv was created. See if there is any use in cross-checking author names or is it better to only focus on arXiv ids and DOIs.
