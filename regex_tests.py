# Valid arxiv ids (post March 2007 identification) that get picked up

# They are always of the form arXiv:YYMM.number (hopefully they are referenced
# like this) so eliminating false positives shouldn't be too hard,
# we just need to make sure the correct number format is preceded by an 
# 'arXiv'
vads_new = [' arXiv:1108.2749v1 [cond-mat.supr-con].']

# Valid arxiv ids (pre March 2007 identification) that get picked up

# These ids are of the following form: archive.subject_class/YYMMnumber
# archives can be
archives = ['astro-ph', 'cond-mat', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph',
            'hep-th', 'math-ph', 'nlin', 'nucl-ex', 'nucl-th', 'physics',
            'quant-ph', 'math', 'CoRR', 'q-bio', 'q-fin', 'stat', 'eess',
            'econ']
# There are a lot of subject classes and we shall see if they are neccessary
vads_old = ['astro-ph/9807138', 'hep-th/9211122', 'hep-ph/0310355', 'nlin/0302024',
            'hep-th/0311063', 'hep-ph/9703423']

# This is also a valid identifier, I can't find where it is from
vads_weird = ['abs/1712.09665']

# Invalid arxiv ids that get picked up
iads = ['DBLP:journals/corr/abs-1812-10812', 'abs/1812.10812, 2018.',
        '\\bibitem{Sharif:2016:ACR:2976749.2978392}', '\\bibitem{NIPS2017_7273}', 
        '(2009)104438']

import re
arxiv_pattern = re.compile('(\d{4}.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?\/\d{7})(v\d+)?', re.IGNORECASE)
print(list(set(re.findall(arxiv_pattern, ' '.join(iads)))))