import os 
from pdf2image import convert_from_path
# path = "test"
lista = os.listdir('.')
poppler_path = r"C:\Users\Daniel\Documents\projects\all-python\bots\actual reports\file_notifier\poppler-23.01.0\Library\bin"
pdf_path = f".{os.sep}test_pdf.pdf"
saving_folder = f".{os.sep}destinyTest"

pages = convert_from_path(pdf_path=pdf_path, poppler_path=poppler_path)
c = 1

for page in pages:
  img_name = f"img-{c}.jpeg"
  page.save(os.path.join(saving_folder,img_name),"JPEG")
  c+=1