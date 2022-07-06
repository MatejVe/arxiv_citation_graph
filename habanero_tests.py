from habanero import Crossref
import time

time1 = time.time()
cr = Crossref()
x = cr.works(ids="10.1016/s1573-4412(07)06063-1")
time2 = time.time()

print(f"Time taken to query the crossref API: {time2-time1:.2f}s")
print(x.keys())
print(x["message"].keys())
print(x["message"]["title"])
print(x["message"]["DOI"])
print(x["message"]["author"])
print(x["message"]["URL"])