from habanero import Crossref

cr = Crossref()
x = cr.works(query_bibliographic='Kim, J.-G., Kim, W.-T., Ostriker, E. C., & Skinner, M. A. 2017, ApJ, 851, 93',
            limit=1)
print(x['status'])
print(x['message-type'])
print(x['message-version'])
print(x['message']['facets'])
print(x['message']['total-results'])
print(x['message']['items-per-page'])
print(x['message']['query'])
print(x['message']['items'][0].keys())
print(x['message']['items'][0]['score'])