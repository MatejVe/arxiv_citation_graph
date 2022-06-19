import urllib.request

base_url = 'http://export.arxiv.org/api/query?';
search_query = urllib.parse.quote("cat:gr-qc")
query = 'search_query=%s&start=%i&max_results=%i' % (search_query, 0, 10)
response = urllib.request.urlopen(base_url+query).read()
print(response)