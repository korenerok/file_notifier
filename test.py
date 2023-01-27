from configparser import ConfigParser
import os 
from pdf2image import convert_from_path
import shutil
config = ConfigParser()
configfile = 'bot.conf'
config.read(f"./{configfile}")



path = f".{os.sep}test"
destiny_folder = f".{os.sep}destinyTest"

def check_files(filepath, filename):
  poppler_path = config['SETTINGS']['poopler_path']
  saving_folder = f"{config['SETTINGS']['convertedPathDuplicate']}{os.sep}{filename}"    
  os.mkdir(saving_folder)
  pages = convert_from_path(pdf_path=filepath, poppler_path=poppler_path)
  c = 1
  for page in pages:
    img_name = f"{filename}-{c}.jpeg"
    page.save(os.path.join(saving_folder,img_name),"JPEG")
    c+=1
  shutil.move(filepath, saving_folder)
  



def convert_pdf():  
  path = config['SETTINGS']['destinyPathDuplicate']
  folder = os.listdir(path)
  for filename in folder:
    file = f"{path}{os.sep}{filename}"
    if os.path.isfile(file):
      check_files(file, filename)
      
      
    
    



# pages = convert_from_path(pdf_path=pdf_path, poppler_path=poppler_path)
