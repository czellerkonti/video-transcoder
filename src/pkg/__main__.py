# encoding: utf-8
'''
Created on 10.04.2017

@author: Konstantin Czeller
'''

import sys,os,logging,shutil,argparse,datetime, time
from os import system
from helpers.utils import *
from helpers.stats import *
from helpers.classes import *
from helpers.config import *
from helpers.logger import Logger




py_version = sys.version_info[0]
l = Logger(Configuration.logfile, Configuration.log_date_format)

logger = l.getLogger()

def collect_videos(dir, extensions, posts, encode_identifiers, analyze):
    res = []
    for root, dirs, files in os.walk(dir):
        for file in files:
            
            if str(file).lower().endswith(extensions):
                
                full_file = os.path.join(root,file)
                if any(ext in file for ext in posts):
                    logger.error("Skipping - encoded file: "+full_file)
                    continue
                if analyze and has_been_encoded(full_file, encode_identifiers):
                    logger.error("Skipping - analyzed as encoded file: " + full_file)
                else:
                    res.append(full_file)

    return res

def get_tasklist_report(videos):
    lst = []
    for video in videos:
        if video.existing:
            lst.append(video.origFile + " - " + video.codec.name + " (forced)")
            continue
        if not os.path.isfile(video.targetFile):
            lst.append(video.origFile + " - " + video.codec.name)
    return lst

# prepare the output filenames and start the encoding
# folder
def process_videos( videos, copy_only, stat ):
    failed_videos = []
    x = 0
    for video in videos:
        x = x + 1
        set_window_title(str(x)  + "/" + str(len(videos)) + " - " + video.origFile + "(" + video.codec.name + ")")
        if copy_only:
            copy_file(video.origFile,video.targetFile)
        else:
            if ( not process_video(video)):
                failed_videos.append(video.targetFile)
            stat.write_row(stat.generate_csv_row(video))
        if (video.getExecCode == 0) and Configuration.delete_input:
            logger.info("Deleting source file: " + video.origFile)
            os.remove(video.origFile)

    return failed_videos

def process_video(video):
    tempfile = Configuration.temppath + os.path.sep + Configuration.tempfile + "." + video.codec.container
    encoder = Encoder(Configuration.logger, Configuration.ffmpeg, Configuration.extraopts, tempfile)
    if Configuration.paranoid and any(os.path.isfile(generate_output_path(video.origFile,x)) for x in CODECS.keys()):
        logger.error(video.origFile + ' has been already transcoded with an other template, PARANOID mode is on')
        video.setExecCode(0)
        return

    #        logger.error(videofile + " has been already transcoded with an other template!")
     #       return -2

    if video.forced: logger.warning("Forcing re-encode: " + video.origFile)

    video.setStartTime()
    ret = encoder.encode(video)
    video.setStopTime()
    video.setExecCode(ret)

    if ret == 0:
        logger.warning("done")
        olddate = os.path.getmtime(video.origFile)
        logger.warning("Moving '{}' -> '{}'".format(tempfile,video.targetFile))
        move_temp(tempfile ,video.targetFile, olddate)
        return True
    else:
        logger.warning("Failed to encode video: {} - {} ret: {}".format(video.origFile, video.codec.name, str(ret)))
        return False

def get_temp_file(template):
    ret = Configuration.temppath + os.path.sep + Configuration.tempfile +'.' + CONTAINERS[template]
    print("TEMPFILE: " + ret)
    return

def parse_arguments():
    homeconfigfile = expanduser("~") + os.path.sep + ".config" + os.path.sep + Configuration.progname + os.path.sep + "config.json"
    if os.name == "posix":
        etcconfigfile = "/etc/" + Configuration.progname + os.path.sep + "config.json"
    else:
        etcconfigfile = os.getenv('LOCALAPPDATA') + os.path.sep + Configuration.progname + os.path.sep + "config.json"
    """
    if args.config:
        configfile = args.config
    elif os.path.isfile(homeconfigfile):
        configfile = homeconfigfile
    elif os.path.isfile(etcconfigfile):
        configfile = etcconfigfile
    else:
        print("Config file not found...quit")
        sys.exit(1)
    """
    if os.path.isfile(homeconfigfile):
        configfile = homeconfigfile
    elif os.path.isfile(etcconfigfile):
        configfile = etcconfigfile
    else:
        print("Config file not found...quit")
        sys.exit(1)
    print("Config file: " + configfile)
    Configuration.processConfigFile(configfile)

    parser = argparse.ArgumentParser(description="Transcodes videos in a folder")
    parser.add_argument("-k","--config", help="config file")
    parser.add_argument("-t","--templates", help="Available templates: " + str(list(Configuration.codecs.keys())))
    parser.add_argument("-i","--input", help="Input file/directory")
    parser.add_argument("-m","--temppath", help="Temp directory")
    parser.add_argument("-e","--encoder", help="Path to encoder binary")
    parser.add_argument("-s","--show", help="Show available encoding templates", action="count")
    parser.add_argument("-f","--force", help="Re-encode already encoded videos", action="count")
    parser.add_argument("-p","--paranoid", help="Paranoid skipping", action="count")
    parser.add_argument("-r","--root", help="Copies the encoded file into an other root folder")
    parser.add_argument("-a","--analyze", help="Analyze video formats", action="count")
    parser.add_argument("-c","--copy", help="copy files only, use it only with -r", action="count")
    parser.add_argument("-w","--forcewidth", help="forces the max width scaling to upscale low res videos NOT IMPLEMEMNTED", action="count")
    parser.add_argument("-d","--daemon", help="run in daemon mode", action="count")
    parser.add_argument("-x","--delete", help="Delete source video", action="count")
    parser.add_argument("-y","--delay", help="daemon mode scan delay in seconds")
    parser.add_argument("-v","--verbose", help="increase output verbosity", action="count")
    
    args = parser.parse_args()
    
    if args.input:
        pass
    elif "MASSENTO_INPUT" in os.environ:
        args.input = os.getenv("MASSENTO_INPUT")

    if args.root:
        pass
    elif "MASSENTO_OUTPUT" in os.environ:
        args.root = os.getenv("MASSENTO_OUTPUT")

    if args.delete:
        Configuration.delete_input = True
    if "MASSENTO_DELETE_SOURCE" in os.environ:
        Configuration.delete_input = os.getenv("MASSENTO_DELETE_SOURCE")

    if args.delay:
        Configuration.delay = args.delay
    elif "MASSENTO_SCAN_DELAY" in os.environ:
        Configuration.delay = os.getenv("MASSENTO_SCAN_DELAY")

    try:
        Configuration.delay = int(Configuration.delay)
    except ValueError:
        #Handle the exception
        print("Scan Delay is not a number")
        sys.exit(1)

    if args.templates:
        pass
    elif "MASSENTO_CODECS" in os.environ:
        args.templates = os.getenv("MASSENTO_CODECS")
    Configuration.process_args(args)
    Configuration.logfile=args.input + os.path.sep + Configuration.logfilename

    return args

def get_video_objs(files, stat):
    config = Configuration
    src_root = config.src_root
    dst_root = config.dst_root
    selected_codecs = config.selected_codecs
    force = config.force_encode
    res = []
    for file in files:
        for codec in selected_codecs:
            video = Video(file, src_root, dst_root, selected_codecs[codec], force)
            if config.paranoid and any(os.path.isfile(Video.generate_output_path(file, src_root, dst_root, x)) for x in Configuration.codecs.values()):
                logger.error(video.origFile + ' has been already transcoded with an other template, PARANOID mode is on')
                continue
            if(force or (not video.existing)):
                res.append(video)            
            else:
                stat.write_row(stat.generate_csv_row(video))
                print("Skipping: "+video.origFile)
                if Configuration.delete_input:
                    logger.info("Deleting already processed source file: " + video.origFile)
                    os.remove(video.origFile)

                
    return res

def main():
    args = parse_arguments()
    global logger

    if args.verbose:
        Configuration.loglevel = "DEBUG"
    elif "MASSENTO_LOGLEVEL" in os.environ:
        Configuration.loglevel = os.getenv("MASSENTO_LOGLEVEL")
    
    if not args.input and not args.show:
        print("Input not found.")
        #parser.print_help()
        sys.exit(2)
    
    inputParam = args.input
    print('Input: ' + inputParam)

    Configuration.logger = logger
    print("Selected codecs: ", Configuration.selected_codecs.keys())
    stats = Statistics(Configuration.statfile)
    print("Stats file: " + Configuration.statfile)
    posts = [ "_"+name for name in Configuration.selected_codecs.keys()]
    posts.append("_enc")
    ###################

    stat = Statistics(Configuration.statfile)
    if not os.path.exists(inputParam):
        print(inputParam + ' does not exist...exiting')
        sys.exit(-1)

    if args.daemon:
        print("daemon mode")
        while True:
            inputParam = ((args.input + os.path.sep).replace(os.path.sep*2, os.path.sep))
            Configuration.src_root = inputParam
            #logger.error("Folder processing: "+inputParam)

            # collect_videos_new(src_root, dst_root, selected_codecs, forced):        
            original_files = collect_videos(inputParam, 
                Configuration.extensions, 
                Configuration.selected_codecs, 
                Configuration.encode_identifiers, 
                Configuration.analyze)
            print_list(original_files,"Video List", logger)
            #print(" - DEBUG - force: " + str(Configuration.force_encode))
            videos = get_video_objs(original_files, stat)
            print_list(get_tasklist_report(videos),"Task List", logger)
            failed_videos = process_videos(videos, Configuration.copy_only, stat)
            print_list(failed_videos,'Failed Videos', logger)
            print("finished...waiting %s seconds",Configuration.delay)
            set_window_title("Waiting for job")
            time.sleep(Configuration.delay)



    if os.path.isfile(inputParam):
        logger.error("File processing: \""+inputParam+"\"")
        for c in Configuration.selected_codecs:
            process_videos(c, inputParam)
        sys.exit(0)

    if os.path.isdir(inputParam):
        inputParam = ((args.input + os.path.sep).replace(os.path.sep*2, os.path.sep))
        Configuration.src_root = inputParam
        #logger.error("Folder processing: "+inputParam)

        # collect_videos_new(src_root, dst_root, selected_codecs, forced):        
        original_files = collect_videos(inputParam, 
            Configuration.extensions, 
            Configuration.selected_codecs, 
            Configuration.encode_identifiers, 
            Configuration.analyze)
        print_list(original_files,"Video List", logger)
        my_input("Press a key to continue...")
        print(" - DEBUG - force: " + str(Configuration.force_encode))
        videos = get_video_objs(original_files, stat)
        print_list(get_tasklist_report(videos),"Task List", logger)
        my_input("Press a key to continue...")
        failed_videos = process_videos(videos, Configuration.copy_only, stat)
        print_list(failed_videos,'Failed Videos', logger)
        logger.error("Exit.")

if __name__ == '__main__':
  main()
