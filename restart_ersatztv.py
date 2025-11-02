#!/tools/conda/envs/Plex/bin/python
import os
import subprocess
import datetime
import time

if __name__=="__main__":
    now=datetime.datetime.now()
    todays_date=now.strftime('%Y%m%d')
    tstamp=now.strftime('%Y.%m.%d.%H.%M.%S')
    docker_container='flamedramon-ersatztv2'
    docker_jf='flamedramon-jellyfin'
    log_file='/tools/ersatztv/conf/logs/ersatztv'+todays_date+'.log'
    log=open(log_file,'rt')
    detected_cuvid_error=False
    search_str='No device available for decoder: device type cuda needed for codec h264_cuvid'
    for line in log:
        if search_str in line:
            detected_cuvid_error=True
            print("Error detected!!!! "+line)
            break
    log.close()
    if detected_cuvid_error:
        # shut down the container
        shutdown=subprocess.Popen(['docker', 'container', 'stop', docker_container], shell=False, stderr=subprocess.STDOUT)
        shutdown_c=shutdown.communicate()
        # rename the log file
        os.rename(log_file, log_file+'.moved_at_'+tstamp+'.log')
        # start the container
        start=subprocess.Popen(['docker', 'container', 'start', docker_container], shell=False, stderr=subprocess.STDOUT)
        start_c=start.communicate()
        time.sleep(5)
        jellyfin=subprocess.Popen(['docker', 'container', 'restart', docker_jf], shell=False, stderr=subprocess.STDOUT)
        jellyfin_c=jellyfin.communicate()
        # write a message to my logs dir about it
        f=open('/data/logs/ersatztv_error_detection_'+tstamp+".txt",'wt')
        f.write("A cuvid error was detected in the logs"+'\n')
        f.write(log_file+'\n')
        f.write('was renamed to'+'\n')
        f.write(log_file+'.moved_at_'+tstamp+'.log'+'\n')
        f.write("and the docker container "+docker_container+" was restarted.")
        f.write("We probably didn't need to but "+docker_jf+" was restarted too.")
        f.close()

