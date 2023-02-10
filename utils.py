from datetime import datetime
import mysql.connector 
from configparser import ConfigParser
import os 
from datetime import date
import shutil
import win32print
import win32api
from pdf2image import convert_from_path
import time



config = ConfigParser()
config.read(f"./bot.conf")
settings = config['SETTINGS']
print_folders=settings['printerFolders'].split(',')
providers= settings['providers'].split(',')


def connectionDb():
    try:
        mydb = mysql.connector.connect(
            host=settings['dbhost'],
            user=settings['dbuser'],
            password=settings['dbpassword'],
            database=settings['dbname'],
            auth_plugin="mysql_native_password" 
        )
        return mydb
    except OSError:
        return OSError
    

def add_files(mydb,filepath, filenames,provider,doctype):
    myCursor = mydb.cursor()
    queryString="INSERT INTO faxes (filepath,filename,provider,document_type,created_date) VALUES (%s,%s,%s,%s,%s)"
    now=datetime.now()
    filenames=list(map(lambda x: (filepath,x,provider,doctype,now),filenames))
    myCursor.executemany(queryString,filenames)
    mydb.commit()

def process_unexistent_files(mydb,path,filesInFolder):
    myCursor = mydb.cursor()
    myCursor.execute("SELECT filename FROM faxes WHERE filepath = %s AND processed_date IS NULL",(path,))
    filesNotProcessed=[x[0] for x in myCursor.fetchall()]
    filesThatWereProcessed =list(filter(lambda x: not_inside_list(x,filesInFolder),filesNotProcessed))
    now=datetime.now()
    filesThatWereProcessed= list(map(lambda x:(now,path,x),filesThatWereProcessed))
    for file in filesThatWereProcessed:
        myCursor.execute("UPDATE faxes SET processed_date = %s WHERE filepath = %s AND filename = %s",file)
        mydb.commit()
    return len(filesThatWereProcessed)

def filter_system_files(x,path):
    system_files=["Thumbs.db"]
    valid = True
    valid= valid and (x not in system_files)
    valid= valid and (x.find(".lnk") < 0)
    foldersToSkip= settings['folders_to_skip'].split(',')
    item_path = path + os.sep + x
    valid= valid and not (os.path.isdir(item_path) and x in foldersToSkip)
    return valid

def duplicate(filepath, filenames,doctype):
    for file in filenames:
        source = f"{filepath}{os.sep}{file}"
        destiny = f"{settings['destinyPathDuplicate']}{os.sep}{doctype}"        
        if not os.path.exists(destiny):
            os.mkdir(destiny)
        shutil.copy(source, f"{destiny}{os.sep}{file}")
        
    


def not_inside_list(x,list):
    return x not in list

def scan_folder(mydb,path,provider=None,doctype=None,level=None):
    try:
        if not os.path.exists(path):
            return OSError 
        if not os.path.isdir(path):
            return OSError
        lista = os.listdir(path)
        myCursor =mydb.cursor(buffered=True)
        lista= list(filter(lambda x: filter_system_files(x,path),lista))
        process_unexistent_files(mydb,path,lista)
        fileNameList=[]
        for item in lista:
            item_path = path + os.sep + item
            if os.path.isdir(item_path):
                scan_folder(mydb,item_path,provider,item)
            else:
                fileNameList.append(item)
        myCursor.execute("SELECT filename FROM faxes WHERE filepath = %s AND processed_date IS NULL",(path,))
        filesInFolder=[x[0] for x in myCursor.fetchall()]
        fileNameList= list(filter(lambda x: not_inside_list(x,filesInFolder) ,fileNameList))
        if len(fileNameList) > 0:
            duplicate(path, fileNameList,doctype)            
            add_files(mydb,path,fileNameList,provider,doctype)
        return None
    except OSError:
        return OSError



def record_new_files():
    try:
        mydb = connectionDb()
        for section in config.sections():
            provider= section.format(['']).upper()
            if provider in providers:
                full_path = settings['path'] + os.sep + config.get(section,'folder')
                scan_folder(mydb,full_path,provider)
        mydb.close()

    except OSError:
        return OSError
    return None




#--------function move archive-------------
def create_final_destination(path):
    today=date.today()
    yearFolder = f"{path}{os.sep}{str(today.year)}"
    if not os.path.exists(yearFolder):
        os.mkdir(yearFolder)
    monthFolder = f"{yearFolder}{os.sep}{str(today.month)}"
    if not os.path.exists(monthFolder):
        os.mkdir(monthFolder)
    dayFolder = f"{monthFolder}{os.sep}{str(today.day)}"
    if not os.path.exists(dayFolder):
        os.mkdir(dayFolder)
    return dayFolder

def is_archive_folder(path):
    """return if the last member of the path is archive folder"""
    return path.split(os.sep)[-1].upper() == "ARCHIVE"

def valid_file_for_archive(filename):
    years=[str(x) for x in range(2022,2042)]
    return str(filename)not in years

def categorize_archives():
    folderpaths=os.walk(settings['path'])
    folderpaths=[x[0] for x in folderpaths]
    folderpaths= list(filter(is_archive_folder,folderpaths))  
    for archivefolder in folderpaths:
        archive_files(archivefolder)

def archive_files(path):
    files = os.listdir(path)
    destinationFolder = create_final_destination(path)
    for filename in files:
        if valid_file_for_archive(filename):
            src = f"{path}{os.sep}{filename}"
            destination= f"{destinationFolder}{os.sep}{filename}"
            shutil.move(src, destination)

def count_new_files(provider,update=True):
    mydb = connectionDb()
    mycursor = mydb.cursor()
    mycursor.execute("SELECT id, document_type, filename,toreview from faxes where provider = %s and new = 1 order by document_type,filename asc;",(provider,))
    result = mycursor.fetchall()
    if len(result) > 0:
        files_to_update=[]
        document_type=None
        msj = f"•{provider} ({len(result)} documents):\n"
        for row in result:
            files_to_update.append((str(row[0]), ))
            if row[1]!=document_type:

                msj+=f"    {(row[1].replace('_','',1)).replace('_',' ')}:\n"
                document_type=row[1]
            
            if row[3]:
                msj += f"        •{row[2]} (TO REVIEW)\n"
            else:
                msj += f"        •{row[2]}\n"
        if update:
            mycursor.executemany("UPDATE faxes SET new = 0 WHERE id = %s",files_to_update)
            mydb.commit()
    else:
        msj = f"•{provider}: no new documents\n"

    return msj

def is_in_print_folders(path):
    folder_path=path.split(os.sep)
    document_type = folder_path[-1].upper()
    provider = folder_path[-2].upper()
    return document_type in print_folders and provider in providers

def scan_print_files(path):
    
    files = os.listdir(path)
    files= list(filter(lambda x: filter_system_files(x,path),files))
    printed_files=[] 
    error_msj=""
    for filename in files:
        file = f"{path}{os.sep}{filename}"
        if os.path.isfile(file):
            destination = f"{path}{os.sep}{'ARCHIVE'}"                
            if not os.path.exists(destination):
                os.mkdir(destination)
            win32api.ShellExecute(0, "print", file , None, ".", 0)
            time.sleep(15)
            shutil.move(file, destination)
            printed_files.append((destination,datetime.now(),filename,path))
        elif os.path.isdir(file):
            error_msj+= f"Detected folder in {path} with the name {filename}. Please check.\n"
    mydb = connectionDb()
    mycursor = mydb.cursor()
    mycursor.executemany("UPDATE faxes set new = 0, filepath = %s, processed_date=%s WHERE filename= %s AND filepath= %s",(printed_files))
    mydb.commit()
    if len(error_msj) > 0:
        return error_msj

def print_files():
    win32print.SetDefaultPrinter(settings['printer'])
    folderpaths=os.walk(settings['path'])
    folderpaths=[x[0] for x in folderpaths]
    folderpaths= list(filter(is_in_print_folders,folderpaths))
    
    msj=""
    for folder in folderpaths:        
        result=scan_print_files(folder)
        if result is not None:
            msj+=result
    if len(msj)>0:
        return msj


def count_all_new_files(update_new_flag=True):
    msj=""
    for provider in providers:
        msj+= count_new_files(provider,update_new_flag)
    return msj

def is_hidden_folder(path):
    """return if the last member of the path is archive folder"""
    provider = path.split(os.sep)[-2].upper()    
    return path.split(os.sep)[-1].upper() in settings['hiddenFolders'] and provider in providers

def hidden_folders():
    folderpaths=os.walk(settings['path'])
    folderpaths=[x[0] for x in folderpaths]
    folderpaths= list(filter(is_hidden_folder,folderpaths))  
    try:
        for folder in folderpaths:
            os.system(f"attrib +h {folder}")
    except OSError:
        return OSError

def is_default_folder(path):
    default_folders= list(os.listdir(settings['default']))
    return path.split(os.sep)[-1].upper() in default_folders
     

def scan_folder_to_convert(folderpath):
    files = os.listdir(folderpath)
    files= list(filter(lambda x: filter_system_files(x,folderpath),files))
    error_msj =""
    for filename in files:
        if filename != 'CONVERTED' and filename.endswith(".pdf"):                         
            poppler_path = settings['poopler_path']
            pdf_path= f"{folderpath}{os.sep}{filename}"
            saving_folder = f"{folderpath}{os.sep}CONVERTED"
            if not os.path.exists(saving_folder):  
                os.mkdir(saving_folder)
            pages = convert_from_path(pdf_path=pdf_path, poppler_path=poppler_path)
            c = 1
            for page in pages:
                img_name = f"{filename}-{c}.jpeg"
                page.save(os.path.join(saving_folder,img_name),"JPEG")
                c+=1
            shutil.move(pdf_path, saving_folder)            
        elif filename != 'CONVERTED':
            error_msj+= f"The {folderpath}{os.sep}{filename}. can't convert Please check.\n"
           
             
    if(len(error_msj)>0):
        return error_msj
    else:
        return None
  
        
    
    


def convert_pdf():    
    folderpaths = os.walk(settings['destinyPathDuplicate'])
    folderpaths=[x[0] for x in folderpaths]
    folderpaths=list(filter(is_default_folder,folderpaths))     
    msg = ""
    for folder in folderpaths:      
        result = scan_folder_to_convert(folder)
        if result is not None:
            msg+=result
            
    if len(msg)>0:
        return msg
    
    
    
