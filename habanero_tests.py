from habanero import Crossref
import time

time1 = time.time()
cr = Crossref()
x = cr.works(query="A. Vilenkin, Phys.Rev. D23, 852 (1981)", limit=1)
time2 = time.time()

print(f"Time taken to query the crossref API: {time2-time1:.2f}s")
print(x["message"]["items"][0].keys())
print(x["message"]["items"][0]["author"])
print(x["message"]["items"][0]["DOI"])
print(x["message"]["items"][0]["title"])
