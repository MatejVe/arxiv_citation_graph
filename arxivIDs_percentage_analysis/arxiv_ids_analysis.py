import matplotlib.pyplot as plt
import json

years = []
percs = []
errs = []

with open('arxiv_id_percentage_hep', 'r') as datafile:
    data = datafile.readlines()
    for line in data:
        line = line.strip().split(' ')
        years.append(int(line[0]))
        percs.append(float(line[1]))
        errs.append(float(line[2]))

fig, ax = plt.subplots(1, 1, figsize=(12, 8))
ax.errorbar(x=years, y=percs, yerr=errs, ecolor='black', fmt='ro')
ax.set_ylabel('Percentage of arXiv id references')
ax.set_xlabel('Paper year of publishing')
ax.set_title('Percentage of arXiv id references throughout the years\n papers were taken from the hep-ex category')
plt.tight_layout()
plt.savefig('arxiv_id_percentage_hep')
plt.close()

years = []
percs = []
errs = []

with open('arxiv_id_percentage_grqc', 'r') as datafile:
    data = datafile.readlines()
    for line in data:
        line = line.strip().split(' ')
        years.append(int(line[0]))
        percs.append(float(line[1]))
        errs.append(float(line[2]))

fig, ax = plt.subplots(1, 1, figsize=(12, 8))
ax.errorbar(x=years, y=percs, yerr=errs, ecolor='black', fmt='ro')
ax.set_ylabel('Percentage of arXiv id references')
ax.set_xlabel('Paper year of publishing')
ax.set_title('Percentage of arXiv id references throughout the years\n papers were taken from the grqc category')
plt.tight_layout()
plt.savefig('arxiv_id_percentage_grqc')
plt.close()

with open('arxiv_id_percentage_grqc.json', 'r') as datafile:
    data = json.load(datafile)

years = []
percentage_data = []
for year in data:
    years.append(int(year))
    percentage_data.append([float(perc) for perc in data[year]])

fig, ax = plt.subplots(1, 1, figsize=(12, 8))
ax.boxplot(x=percentage_data, positions=years)
ax.set_ylabel('Percentage of arXiv id references')
ax.set_xlabel('Paper year of publishing')
ax.set_title('Percentage of arXiv id references throughout the years\n papers were taken from the gr-qc category')
plt.savefig('arxiv_id_percentage_median_grqc')
plt.close()

with open('arxiv_id_percentage_hep-ex.json', 'r') as datafile:
    data = json.load(datafile)

years = []
percentage_data = []
for year in data:
    years.append(int(year))
    percentage_data.append([float(perc) for perc in data[year]])

fig, ax = plt.subplots(1, 1, figsize=(12, 8))
ax.boxplot(x=percentage_data, positions=years)
ax.set_ylabel('Percentage of arXiv id references')
ax.set_xlabel('Paper year of publishing')
ax.set_title('Percentage of arXiv id references throughout the years\n papers were taken from the hep-ex category')
plt.savefig('arxiv_id_percentage_median_hepex')
plt.close()