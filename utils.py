from datetime import datetime
import mysql.connector 
from configparser import ConfigParser
import os 
from datetime import date 
import shutil

config = ConfigParser()
config.read(f"./bot.conf")
settings = config['SETTINGS']

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
        providers= settings['providers'].split(',')
        for section in config.sections():
            provider= section.format(['']).upper()
            if provider in providers:
                full_path = settings['path'] + os.sep + config.get(section,'folder')
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

#------------Duplicate function-----------

def scan_duplicate_inbox(path, destiny = settings['destinyPathDuplicate']):
    dir = os.listdir(path)
    for file in dir:    
        check = os.path.join(path, file)    
        edited = os.path.getmtime(check)    
        if os.path.isfile(check):     
            conection = connectionDb() 
            myCursor = conection.cursor()      
            myCursor.execute("SELECT filepath, filename, filecreation FROM duplicate where   filename = '{}' and filecreation = '{}';".format(path, file, edited))
            result = myCursor.fetchall()
        
            if len(result) == 0: 
                myCursor.execute("INSERT INTO duplicate (filepath, filename, filecreation, dateduplicate) VALUES ('{}','{}','{}', current_timestamp);".format(path, file, edited) )
                conection.commit()
                
                destinyfinal = f"{destiny}{os.sep}{file}"         
                shutil.copy(check, destinyfinal)            
                 
                       
        
        elif os.path.isdir(check):
            destinyF = f"{settings['destinyPathDuplicate']}{os.sep}{file}"
            if not os.path.exists(destinyF):
                os.mkdir(destinyF)        
            newPath = os.path.join(path, file)      
            scan_duplicate_inbox(newPath, destinyF)
            
        conection.close()
        

def new_scan_provider(provider):
    folder = f"{settings['path']}{os.sep}{provider}"
    scans = os.listdir(folder)
    folderReview =scans.append("To Review")
    
    count= 0
   
    for folder in scans: 
        mydb = connectionDb()
        mycursor = mydb.cursor()   
        dir = ""     
        mycursor.execute("SELECT document_type, provider, filename, filepath from faxes where document_type = %s and provider = %s and new = 1;", (folder, provider) )
        result = mycursor.fetchall()
        if len(result) != 0:
            print(result)
            msj = f"In Dr.{provider} folder had a new documents in the next folders: \n"          
            
            for row in result:  
                
                # print(dir)                 
                if dir != row[0]:
                    # if x[0].upper() == 'TO REVIEW':
                    #     filepath = x[3].split(os.sep)[-2]
                    #     msj += filepath         
                    msj += f"{row[0]}:\n"                  
                    msj += f"{row[2]}\n"                    
                    dir = row[0]
                   
                elif dir ==row[0]:
                    msj += f"{row[2]}\n"
                    #print(x[2])
                                
                
                # #if x[0].upper() != 'TO REVIEW':
                # # count += 1   
                # # test = x[3].split(os.sep)[-2]            
                # # msj = f"{test}\n"
                # # msj +=f"{x[0]}:\n"
                # # msj += f"{count}. {x[2]}. \n"    

          
        
    return msj
                # if x[0].upper() == 'TO REVIEW':
                #     print(x[3].split(os.sep)[-2])
            

print(new_scan_provider("ROSS"))