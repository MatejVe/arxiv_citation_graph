from crossref.restful import Works

works = Works()
w1 = works.query(
    bibliographic="F Cooper, J N Ginocchio, and A Wipf. Supersymmetry, operator transformations and exactly solvable potentials. J. Phys. A, 22(17):3707–3716, sep 1989."
)

for item in w1:
    bestItem = item
    break

print(bestItem.keys())
print(bestItem["title"])
print(bestItem["author"])
print(bestItem["DOI"])
print(bestItem["type"])
print(bestItem["published-print"]["date-parts"][0])

w2 = works.query(bibliographic="Some random gibberish, nema ništa korisno")

for item in w2:
    bestItem = item
    break

print(bestItem)
