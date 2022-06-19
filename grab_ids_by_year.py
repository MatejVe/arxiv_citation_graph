import urllib.request
import json
import time
import feedparser

# Base api query url
base_url = 'http://export.arxiv.org/api/query?';

papers_by_year = {str(year):[] for year in range(1992, 2023)}

# Search parameters
search_query = urllib.parse.quote("cat:hep-ex")
i = 0
results_per_iteration = 100
wait_time = 3
print('Searching arXiv for %s' % search_query)
year = 2022

grabed_entries = []
while (int(year) > 1992): #stop requesting when we reach the year 2022
    print({year:len(papers_by_year[year]) for year in papers_by_year})
    print("Results %i - %i" % (i,i+results_per_iteration))
    
    query = 'search_query=%s&start=%i&max_results=%i&sortBy=submittedDate&sortOrder=descending' % (search_query,
                                                         i,
                                                         results_per_iteration)

    # perform a GET request using the base_url and query
    response = urllib.request.urlopen(base_url+query).read()

    # parse the response using feedparser
    feed = feedparser.parse(response)
    print(f'Grabed {len(feed.entries)} entries.')

    # Save the number of grabed entries
    grabed_entries.append(len(feed.entries))
    if len(grabed_entries) > 4:
        # Terminate if we keep getting empty responses
        if all([grabed == 0 for grabed in grabed_entries[-10:]]):
            break
    # Run through each entry, and print out information
    for entry in feed.entries:
        #print('Title:  %s' % entry.title)
        #print('arxiv-id: %s' % entry.id.split('/abs/')[-1])
        #feedparser v4.1 only grabs the first author
        #print('First Author:  %s' % entry.author)
        #print('Year published: %s' % entry.published[0:4])
        year = entry.published[0:4]
        if year in papers_by_year.keys() and len(papers_by_year[year]) < 50:
            papers_by_year[year].append(entry.id.split('/abs/')[-1])
    # Sleep a bit before calling the API again
    print(year)
    print('Bulk: %i' % 1)
    i += results_per_iteration
    time.sleep(wait_time)

with open("arxiv_ids_by_years_all_hep-ex", "w") as outfile:
    json.dump(papers_by_year, outfile)