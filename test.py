import chardet

def get_data_string(filename):
    """
    Here we read the data file and decode the byte string
    """
    try:
        with open(filename, 'rb') as f:
            contents = f.read()
    except:
        # So far we had no issue with this, but if it happens we should 
        # catch the exception
        print("Can't read file?")
        raise
    else:
        # We need to check how this byte string is encoded
        detection = chardet.detect(contents)
        encoding = detection["encoding"]
        print("encoding = ", encoding)
        if encoding is None:
            # Let's try utf-8 and ignore any errors
            contents = contents.decode('utf-8', 'ignore')
        else:
            # Even though we tried to determine the encoding above,
            # it still happens that we get errors here
            contents = contents.decode(encoding, 'ignore')
        return contents

contents = get_data_string('dummy/1902_00678.folder_dummy/Paper_submit.tex')

if contents.find(r'\bibitem') > -1:
    # and after the appearance of '\end{thebibliography}
    first_bibitem = contents.find(r'\bibitem')
    bibliography_end = contents.find(r'\end{thebibliography}')
    contents = contents[first_bibitem:bibliography_end]
    list_of_bibitems = contents.split(r'\bibitem')
    list_of_bibitems = list(filter(lambda item: item, list_of_bibitems))
    list_of_bibitems = [item.strip() for item in list_of_bibitems]
    print(list_of_bibitems[-1])