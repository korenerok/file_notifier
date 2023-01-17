from datetime import datetime
import mysql.connector 
from configparser import ConfigParser
import os 
from datetime import date 
import shutil




config = ConfigParser()
configfile = 'bot.conf'
config.read(f"./{configfile}")
settings = config['SETTINGS']
path = format(settings['path'])
providers= settings['providers'].split(',')
dbFaxes = settings['dbname']
dest = settings['destinyPathDuplicate']

def connectionDb(db):
    try:
        mydb = mysql.connector.connect(
            host=settings['dbhost'],
            user=settings['dbuser'],
            password=settings['dbpassword'],
            database=db,
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
        mydb = connectionDb(dbFaxes)
        for section in config.sections():
            provider= section.format(['']).upper()
            if provider in providers:
                full_path = path + os.sep + config.get(section,'folder')
                scan_folder(mydb,full_path,provider)
        mydb.close()

    except OSError:
        return OSError
    return None



#------------------funciones agregadas Daniel ----------------------
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

def categorize_archives():
    #find ARCHIVE folders
    folderpaths=os.walk(".")
    folderpaths=[x[0] for x in folderpaths]
    folderpaths= list(filter(is_archive_folder,folderpaths))
    for archivefolder in folderpaths:
        archive_files(archivefolder)

def archive_files(path):
    files = os.listdir(path)
    destinationFolder = create_final_destination(path)
    for file in files:
        if os.path.isfile(file):
            src = f"{path}{os.sep}{file}"
            destination= f"{destinationFolder}{os.sep}{file}"
            shutil.move(src, destination)
     
#------------Duplicate function-----------

def scan_duplciate_inbox(path, destiny = dest):
    dir = os.listdir(path)
    for file in dir:    
        check = os.path.join(path, file)    
        edited = os.path.getmtime(check)    
        if os.path.isfile(check):    
            print(file)   
            conection = connectionDb(dbFaxes) 
            myCursor = conection.cursor()      
            myCursor.execute("SELECT filepath, filename, filecreation FROM duplicate where filepath = '{}' and filename = '{}' and filecreation = '{}';".format(path, file, edited))
            result = myCursor.fetchall()
        
            if len(result) == 0: 
                myCursor.execute("INSERT INTO duplicate (filepath, filename, filecreation, dateduplicate) VALUES ('{}','{}','{}', current_timestamp);".format(path, file, edited) )
                conection.commit()
                destinyfinal = f"{destiny}\{file}"    
                print("estamos guardando ")        
                shutil.copy(check, destinyfinal)           
                       
        
        elif os.path.isdir(check):
            destinyF = f"{dest}\{file}"
            if not os.path.exists(destinyF):
                os.mkdir(destinyF)        
            newPath = os.path.join(path, file)      
            scan_duplciate_inbox(newPath, destinyF)