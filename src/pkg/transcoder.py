'''
Created on 10.04.2017

@author: Konstantin Czeller
'''

import sys,os,logging,shutil,argparse
from os import system

# logs the process here
LOGFILE="c:\\tmp\\actual.txt"
TEMPFILE="c:\\tmp\\temp.mp4"
TASK_LIST="c:\\tmp\\list.txt"
SEARCHDIR="$1"
EXTENSIONS=('avi','mpg','mpeg','mpv','mp4','mkv','mov')
FFMPEG="d:\\Tools\\ffmpeg-3.2.4-win64-shared\\bin\\ffmpeg.exe"
EXTRAOPTS="-v info -y -i"

SUBDIR="encode"
LOG_DATE_FORMAT="%Y-%m-%d %H:%M:%S"

CODECS = {}
CODECS["mp3"]="-c:v copy -c:a libmp3lame -q:a 5 -"
CODECS["x264"]="-c:v libx264 -preset veryslow -crf 20 -tune film -c:a copy -movflags +faststart"
CODECS["x265"]="-c:v libx265 -preset slow -crf 20 -c:a copy -movflags +faststart"
CODECS["x265_aac"]="-c:v libx265 -preset slow -crf 20 -c:a aac -ab 160k -movflags +faststart"
CODECS["x264_aac"]="-c:v libx264 -preset veryslow -crf 20 -tune film -c:a aac -ab 160k -movflags +faststart"

POSTS = list("_" + post for post in CODECS.keys())
POSTS.append("_enc")
SELECTED_CODECS = []
FILES = []

system("title: new title")

try:
    os.remove(LOGFILE)
    os.remove(TEMPFILE)
    os.remove(TASK_LIST)
except (OSError) as e:
    print ("")  


def config_logger(logfile):
    logFormatter = logging.Formatter('%(asctime)s %(message)s',datefmt=LOG_DATE_FORMAT)
    rootLogger = logging.getLogger()

    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(logFormatter)
    fileHandler.setLevel(logging.INFO)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(logging.WARNING)
    rootLogger.addHandler(consoleHandler)
    rootLogger.setLevel(logging.WARNING)
    return rootLogger

logger = config_logger(LOGFILE)

def encode(codec, inputvideo):
    if codec not in CODECS.keys():
        logger.error("Unknown codec: "+codec)
        return -1
    encode_options = CODECS.get(codec)
    logger.warning("Transcoding "+inputvideo+" - "+codec)    command = FFMPEG + " " + EXTRAOPTS + " \"" + inputvideo + "\" " + encode_options + " " + TEMPFILE
    logger.error(command)
    ret = os.system(command)
    logger.warning("ret: "+str(ret))
    return ret

def move_temp( target, date ):
    targetdir = os.path.dirname(target)
    if not os.path.exists(targetdir):
        os.makedirs(targetdir)
    shutil.move(TEMPFILE,target)
    os.utime(target, (date, date))
    return

def encode_test( codec, inputvideo, outputvideo ):
    return

def collect_videos(dir):
    for root, dirs, files in os.walk(dir):
        for file in files:
            if str(file).lower().endswith(EXTENSIONS):
                if  any(ext in file for ext in POSTS):
                    logger.error("Skipping - encoded file: "+os.path.join(root,file))
                else:
                    print("adding: " + file)
                    FILES.append(os.path.join(root,file))

# print/write out the found videos
def print_videolist():
    for file in FILES:
            logger.error(file)

def print_tasklist():
    for file in FILES:
        for c in SELECTED_CODECS:
            targetfile = generate_output_path(file, c)
            if not os.path.isfile(targetfile):
                logger.error(file + " - " + c)

# prepare the output filenames and start the encoding
def process_folder( folder ):
    for c in SELECTED_CODECS:
        for file in FILES:
            process_video(c,file)

def process_video(codec, videofile):
    targetfile = generate_output_path(videofile,codec)
    # file exists
    if os.path.isfile(targetfile):
        logger.error(targetfile + " has been already transcoded")
        return -1
    
    ret = encode(codec,videofile)
    if ret == 0:
        logger.warning("done")
        olddate = os.path.getmtime(videofile)
        move_temp(targetfile, olddate)
    else:
        logger.warning("Failed to encode video: " + videofile + " - " + codec + " ret: " + str(ret))

def generate_output_path(videofile, marker):
    fname = os.path.splitext(os.path.basename(videofile))[0]+"_"+marker+".mp4"  
    targetdir=os.path.dirname(videofile)+os.path.sep+marker
    return os.path.join(targetdir,fname)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Transcodes videos in a folder")
    parser.add_argument("-c","--codecs", help="available codecs: " + str(list(CODECS.keys())))
    parser.add_argument("-i","--input", help="Input folder/directory")
    parser.add_argument("-s","--show", help="Show available encoding templates", action="count")
    args = parser.parse_args()
    
    if not args.input and not args.show:
        print("Input not found.")
        parser.print_help()
        sys.exit(2)

    return args

def cleanup_logs():
    try:
        os.remove(LOGFILE)
        os.remove(TEMPFILE)
        os.remove(TASK_LIST)
    except (OSError) as e:
        print ("")  

def main():
    global SELECTED_CODECS
    args = parse_arguments()    
    
    inputParam = args.input
    if args.show:
        print("Available templates")
        print("")
        for key in CODECS.keys():    
            print(key+":    " + CODECS.get(key))
        sys.exit(1)
    
    if not args.codecs:
        SELECTED_CODECS = CODECS.keys()
    else:
        SELECTED_CODECS = args.codecs.split(",")
        WRONG_CODECS = []
        for codec in SELECTED_CODECS:
            if codec not in CODECS.keys():
                print("Unknown codec: " + str(codec))
                WRONG_CODECS.append(codec)
        for c in WRONG_CODECS:
            SELECTED_CODECS.remove(c)
        if not SELECTED_CODECS:
            print("")
            print("There is no known codec given.")
            print("Known codecs: " + str(CODECS.keys()))
            print("Exiting...")
            sys.exit(1)
    
    print("Selected codecs: ", SELECTED_CODECS)
    
    if os.path.isfile(inputParam):
        logger.error("File processing: \""+inputParam+"\"")
        for c in SELECTED_CODECS:
            process_video(c, inputParam)
    
    if os.path.isdir(inputParam):
        logger.error("Folder processing: "+inputParam)
        collect_videos(inputParam)
        logger.error(" --- Video List ---")
        print_videolist()
        input("Press a key to continue...")
        logger.error(" --- Task List ---")
        print_tasklist()
        input("Press a key to continue...")
        process_folder(inputParam)
        logger.error("Exit.")
main()