from datetime import datetime
import mysql.connector 
from configparser import ConfigParser
import os 
from datetime import date
import shutil
import win32print
import win32api
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
    years=[x for x in range(2022,2042)]
    return (os.path.isfile(filename)) or (os.path.isdir(filename) and filename not in years)

def categorize_archives():
    #find ARCHIVE folders
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

def count_new_files(provider):
    mydb = connectionDb()
    mycursor = mydb.cursor()
    mycursor.execute("SELECT id, document_type, filename,toreview from faxes where provider = %s and new = 1 order by document_type,filename asc;",(provider,))
    result = mycursor.fetchall()
    if len(result) > 0:
        files_to_update=[]
        document_type=None
        msj = f"In Dr.{provider} folder there are {len(result)} new documents:\n"
        for row in result:
            files_to_update.append((str(row[0]), ))
            if row[1]!=document_type:
                msj+=f"{row[1]}:\n"
                document_type=row[1]
            if row[3]:
                msj += f"{row[2]}(TO REVIEW)\n"
            else:
                msj += f"{row[2]}\n"
        mycursor.executemany("UPDATE faxes SET new = 0 WHERE id = %s",files_to_update)
        mydb.commit()
    else:
        msj = f"In Dr.{provider} folder there are no new documents\n"
    return msj

## To be tested 

def is_in_print_folders(path):
    folder_path=path.split(os.sep)
    document_type = folder_path[-1].upper()
    provider = folder_path[-2].upper()
    return document_type in print_folders and provider in providers

def scan_print_files(path):
    files = os.listdir(path)
    files= list(filter(lambda x: filter_system_files(x,path),files))
    printed_files=[] 
    for filename in files:
        file = f"{path}{os.sep}{filename}"
        if os.path.isfile(file):
            destination = f"{path}{os.sep}{'TO REVIEW'}"                
            if not os.path.exists(destination):
                os.mkdir(destination)
            win32api.ShellExecute(0, "print", file , None, ".", 0)
            time.sleep(15)
            shutil.move(file, destination)
            printed_files.append((destination,datetime.now(),filename,path))
        elif os.path.isdir(file):
            return f"I detect a folder in {path} with the name {filename}  please check"
    mydb = connectionDb()
    mycursor = mydb.cursor()
    mycursor.executemany("UPDATE faxes set toreview = 1, filepath = %s, processed_date=%s WHERE filename= %s AND filepath= %s",(printed_files))
    mydb.commit()

def print_files():
    win32print.SetDefaultPrinter(settings['printer'])
    folderpaths=os.walk(settings['path'])
    folderpaths=[x[0] for x in folderpaths]
    folderpaths= list(filter(is_in_print_folders,folderpaths))
    for folder in folderpaths:        
       return scan_print_files(folder)

#------------------funciones agregadas por Daniel aún por revisión ----------------------
#------------Duplicate function-----------

def checking_proccesed_duplciates(mydb,path, filesInFolder):    
    myCursor = mydb.cursor()
    myCursor.execute("SELECT filename FROM duplicate where filepath = %s and processed_date IS NULL", (path,))
    filesNotProcessed = [x[0] for x in myCursor.fetchall()]
    filesThatWereProcessed =list(filter(lambda x: not_inside_list(x,filesInFolder),filesNotProcessed))
    now=datetime.now()
    filesThatWereProcessed = list(map(lambda x:(now,path,x),filesThatWereProcessed))
    for file in filesThatWereProcessed:
        myCursor.execute("UPDATE duplicate SET processed_date = %s WHERE filepath = %s AND filename = %s",file)
        mydb.commit()
    return len(filesThatWereProcessed)
        
def add_duplicates(mydb, filepath, filenames):
    myCursor = mydb.cursor()
    querySQL = " INSERT INTO duplicate (filepath, filename, dateduplicate) VALUES (%s,%s,%s)"
    now = datetime.now()   
    filenames = list(map(lambda x:(filepath,x,now), filenames))   
    copy_files(filenames)
    myCursor.executemany(querySQL, filenames)
    mydb.commit()
        
   
def copy_files(movelist):
    for item in movelist:
        src = f"{item[0]}{os.sep}{item[1]}"
        destiny = f"{settings['destinyPathDuplicate']}{os.sep}{item[1]}"
        shutil.copy(src, destiny)

def duplicate():
    try:
        mydb = connectionDb()
        myCursor =mydb.cursor(buffered=True)
        path = settings['inboxPath']    
        files = os.listdir(path) 
        files= list(filter(lambda x: filter_system_files(x,path),files)) 
        checking_proccesed_duplciates(mydb, path, files)   
        fileNameList=[] 
        for file in files:
            filePath = f"{path}{os.sep}{file}"
            if os.path.isfile(filePath):
                fileNameList.append(file)
            elif os.path.isdir(filePath):
                return f"I detect a folder in \\xr-fs1\Shares\INT_ROSS\FAX\INBOX with the name {file}  please check"
        myCursor.execute("SELECT filename FROM duplicate WHERE filepath = %s AND processed_date IS NULL",(path,))                
        filesInFolder=[x[0] for x in myCursor.fetchall()]                
        fileNameList = list(filter(lambda x: not_inside_list(x,filesInFolder), fileNameList ))
        
        if len(fileNameList) > 0:
            add_duplicates(mydb, path, fileNameList)
        mydb.close()
        
              
    except OSError:
      return OSError

def count_all():
    mydb = connectionDb()
    mycursor = mydb.cursor()
    mycursor.execute("SELECT id, provider, document_type, filename,toreview from faxes where new = 1 order by document_type,filename asc;")