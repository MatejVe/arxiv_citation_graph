from PyPDF2 import PdfReader

reader = PdfReader("9408002.pdf")

text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"

references = text[text.rfind("REFERENCES") :]  # .split("\n")[1:]
print(references)
