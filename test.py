from lmqg import TransformersQG
from pypdf import PdfReader

reader = PdfReader('UNIT -6.pdf')

print(len(reader.pages))

# creating a page object
page = reader.pages[0]

model = TransformersQG(language="en")
# context = "William Turner was an English painter who specialised in watercolour landscapes. He is often known " \
#           "as William Turner of Oxford or just Turner of Oxford to distinguish him from his contemporary, " \
#           "J. M. W. Turner. Many of Turner's paintings depicted the countryside around Oxford. One of his " \
#           "best known pictures is a view of the city of Oxford from Hinksey Hill."

context = page.extract_text()
print(context)

# qa = model.generate_qa(context)
# print(qa)