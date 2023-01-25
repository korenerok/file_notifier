import os 
import pdf2jpg
from pdf2jpg import pdf2jpg
import os
import sys
from pdf2image import convert_from_path
# path = "test"
lista = os.listdir('.')

# for file in lista:
#   filepath = f"{path}{os.sep}{file}"
#   if os.path.isfile(filepath):
#     #print(file)
#     images = convert_from_path(filepath)
#     print(len(images))

print(os.path.isfile('./test_pdf.pdf'))

print(os.path.isdir('./destinationTest'))
  
source = 'test_pdf.pdf'
destiny = './destinationTest/test_pdf.jpg'
# Final = pdf2jpg.convert_pdf2jpg(  source , destiny )
# print(Final)

images = convert_from_path('test_pdf.pdf', 500) #Read pdf file
for i in images:
  i.save('out.jpg', 'JPEG') 