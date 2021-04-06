#!/usr/bin/env python3.4
import re
import subprocess
import logging
import sys,os
import datetime
try:
	import cPickle as pickle
except ImportError:
	import pickle
 
##############
# New Addons #
##############
# Alarm in case the K8 API is no working
# All input variables can be automated
# To RECOVER all events
# A second DB file to record issues in the time ( last 25h )
 
########################################################################################################################
# Constants & Global Variables
########################################################################################################################
arguments = ''
debug=False
cmd='kubectl get pods -o wide'
count_reboots = 0
current_time = datetime.datetime.now()
empty=[] # Timesheet DB data
# all var in a dict.
my_global_dict = dict({
	'var_zab_send_server'      	: "**********", 
	'var_zab_send_host'        	: "**************************",
	'var_zab_send_item_name'   	: "python_external_message",
	'var_zab_send_trigger_recover' : "recover_all"
	})
my_global_dict['reboot_DB_pick_file'] = "/tmp/zabbix_%s_%s_%s.pickle" % (os.path.basename(__file__), os.getuid(),'docker-reboot')
my_global_dict['time_DB_pick_file']   = "/tmp/zabbix_%s_%s_%s.pickle" % (os.path.basename(__file__), os.getuid(),'docker-reboot-time_DB') 
 
for line in sys.argv[1:] : arguments = arguments + ' ' + line
regex_result = re.search("debug",arguments)
if regex_result : debug=True
if debug:
	print("Debug is ON!")
	logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig()
 
########################################################################################################################
# Execute Command
########################################################################################################################
def exec_command(my_command,my_timeout=6,my_splitter=' '):
    logger = logging.getLogger('def_exec_command')
    logger.debug('To execute command: {0}'.format(my_command))
    if not my_command:
    	my_command='date'
    if type(my_command) is str:
        command_v2 = my_command.split(my_splitter)
    if type(my_command) is list:
    	command_v2 = my_command
    try:
        my_out=subprocess.check_output(command_v2,timeout=my_timeout)
    	pass
    except Exception as exc:
        	logger.error('ERROR [{0}] {1}'.format(exc.__class__.__name__, exc))
        	return False
    return my_out
 
########################################################################################################################
# Get Pickle data
########################################################################################################################
def get_pickle_data(my_file):
    logger = logging.getLogger('def_get_pickle_data')
    logger.debug('To read pickle file')
    if os.path.exists(my_file):
        try:
        	data = pickle.load(open(my_file, "rb"))
    	except Exception as exc:
            logger.error('ERROR [{0}] {1}'.format(exc.__class__.__name__, exc))
            return False
    	return data
    else:
    	return False

########################################################################################################################
# Set Pickle data
########################################################################################################################
def set_pickle_data(my_file,my_data):
    logger = logging.getLogger('def_set_pickle_data')
    logger.debug('To write pickle file')
    try:
    	pickle.dump(my_data, open(my_file, "wb"))
    except Exception as exc:
    	logger.error('ERROR [{0}] {1}'.format(exc.__class__.__name__, exc))
    	return False
	return True
 
########################################################################################################################
# GENERAL Send Message On Timesheet Change
########################################################################################################################
def general_send_message_on_timesheet_change(my_message):
    logger = logging.getLogger('def_general_send_message_on_timesheet_change')
    logger.debug('general_send_message_on_timesheet_change --> ' + str(my_message))
    cs=["zabbix_sender","-z",my_global_dict["var_zab_send_server"],"-s",my_global_dict["var_zab_send_host"],"-k",my_global_dict["var_zab_send_item_name"],"-o", '"'+str(my_message)+'"']
    exec_command(cs)
    return True
 
########################################################################################################################
# Send Message On Timesheet Change
########################################################################################################################
def send_message_on_timesheet_change(my_name,my_reboots,my_diff_time,my_timestamp):
    logger = logging.getLogger('def_send_message_on_reboot')
    logger.debug('To report a reboot')
    s= '{0} was rebooted {1} times in the last {2} and has lived for {3}'.format(my_name,my_reboots,my_diff_time,my_timestamp)
    cmd2 = "********'{0}'".format(s)
    logger.debug('Command to be EXECUTED ! : [{0}]'.format(cmd2))
    cs=["zabbix_sender","-z","*********","-s","*************","-k","python_external_message","-o",s]
    exec_command(cs)
    return True

########################################################################################################################
# Add Timesheet Record
########################################################################################################################
def add_timesheet_record(my_name,my_reboots,my_current_time):
    global timesheet_2d
    logger = logging.getLogger('def_add_timesheet_record')
    my_current_time_str = my_current_time.strftime("%Y-%m-%d %H:%M:%S.%f")
    timesheet_2d.append([my_name,my_reboots,my_current_time_str])

########################################################################################################################
# Remove Old Timesheet Record
########################################################################################################################
def remove_timesheet_record(my_current_time):
    global timesheet_2d
    new_timesheet_2d = []
    logger = logging.getLogger('def_remove_timesheet_record')
    for row in range(len(timesheet_2d)):
        #FIND DIFFERENCE IN TIMESHEET
        prev_time_str = timesheet_2d[row][2]
        prev_time_obj = datetime.datetime.strptime(prev_time_str, '%Y-%m-%d %H:%M:%S.%f')
        diff = (current_time - prev_time_obj)

        # REMOVE OLD RECORDS THAT ARE OLDER THAN 2 MONTHS
        if diff.total_seconds() < 5259492:
            new_timesheet_2d.append(row)
    return new_timesheet_2d
    
########################################################################################################################
# Calculate Reboots Since Timesheet
########################################################################################################################
def calculate_timesheet(my_name,my_reboots,my_current_time,my_timestamp):
    global timesheet_2d
    logger = logging.getLogger('def_calculate_timesheet')
    for row in range(len(timesheet_2d)):
        if len(timesheet_2d[row]) < 2: #CHECK IF ROW IS EMPTY
        	logger.debug('Time DB has an empty line.')
       
        if timesheet_2d[row][0] == my_name: #IF NAME EXISTS IN TIMESHEET DATABASE
        	#FIND DIFFERENCE IN TIMESHEET
            prev_time_str = timesheet_2d[row][2]
            prev_time_obj = datetime.datetime.strptime(prev_time_str, '%Y-%m-%d %H:%M:%S.%f')
            diff = (current_time - prev_time_obj)
        	#SEND MESSAGE
            send_message_on_timesheet_change(timesheet_2d[row][0],timesheet_2d[row][1],diff,my_timestamp)

        elif timesheet_2d[row][0] != my_name:
            #POPULATE DATABASE
            add_timesheet_record(timesheet_2d[row][0],timesheet_2d[row][1],my_current_time)
            #SEND MESSAGE
            send_message_on_timesheet_change(timesheet_2d[row][0],timesheet_2d[row][1],diff,my_timestamp)

    	else:
        	logger.debug('ERROR: Cannot match pod name with Timesheet DB')

########################################################################################################################
# MAIN
########################################################################################################################
logger = logging.getLogger('_Main_')
 
out = exec_command(cmd)
if type(out) is bool :
	logger.debug('Failed command: {0}'.format(cmd))
	general_send_message_on_timesheet_change("Failed to execute command: " + cmd + "  Possible issue with K8 API !!! " )
	exit() # Error
if type(out) is bytes:
	logger.debug('Successfully executed command: {0}'.format(cmd))
#Read Timesheet DB data
#The old recorded issues
timesheet_2d = get_pickle_data(my_global_dict['time_DB_pick_file'])
if type(timesheet_2d) is bool:
	# no any old data
	logger.debug('Pickle Timesheet DB file is missing.')
	logger.debug('Writing the Timesheet DB pickle file.')
	set_pickle_data(my_global_dict['time_DB_pick_file'],empty) # Empty Timesheet DB data file
if type(timesheet_2d) is list:
	logger.debug('Successfully Exported Timesheet data')
 
#Create new_pods_2d array
#The current pod status
new_pods_2d=[]
new_pods_array=out.decode('cp1251').split('\n')
for i in range(len(new_pods_array)):
    ch=re.split(r"\s\s+",new_pods_array[i])
	#need a check for len()
    new_pods_2d.append(ch)
 
#Read old_pods_2d DB data
#The OLD pod status
 
old_pods_2d = get_pickle_data(my_global_dict['reboot_DB_pick_file'])
if type(old_pods_2d) is bool:
	# no any old data`
	logger.debug('Pickle file is missing.')
	logger.debug('Writing the pickle file.')
	set_pickle_data(my_global_dict['reboot_DB_pick_file'] ,new_pods_2d)
if type(old_pods_2d) is list:
	# we have old data
    logger.debug('Successfully Exported Old Pods data')
    for old_row in range(len(old_pods_2d)):
        for new_row in range(len(new_pods_2d)):
            if old_pods_2d[old_row][0] == new_pods_2d[new_row][0]:
                logger.debug('Successfully matched pod name : {0}'.format(old_pods_2d[old_row][0]))
            	#match docker name
            	if len(old_pods_2d[old_row]) < 4:
                	#in case the 2d list is small - doesn't have [3]= reboots; We can have empty rolls
                	logger.debug('ERROR N1 list index <4 : "{0}"'.format(old_pods_2d[old_row][0]))
            	elif len(new_pods_2d[new_row]) < 4:
                	#in case the 2d list is small - doesn't have [3]= reboots; We can have empty rolls
                	logger.debug('ERROR N2 list index <4 : "{0}"'.format(new_pods_2d[new_row][0]))
            	else:
                    if old_pods_2d[old_row][3].isdigit() and new_pods_2d[new_row][3].isdigit():
                    	#2 integer values
                    	old_reboots = int(old_pods_2d[old_row][3])
                    	new_reboots = int(new_pods_2d[new_row][3])
                    	if new_reboots > old_reboots:
                            if new_reboots > 2:
                            	# !!!! REBOOTS !!!!
                            	logger.debug(' >>> pod reboots >>> : {0} with {1} reboots in the last {3}'.format(new_pods_2d[new_row][0],new_pods_2d[new_row][3],new_pods_2d[new_row][4]))
            	                ii=new_reboots-old_reboots
                            	count_reboots += ii
                            	calculate_timesheet(new_pods_2d[new_row][0],new_pods_2d[new_row][3],current_time,new_pods_2d[new_row][4])
                    else:
                        # in case the int is not an int :D
                    	logger.debug('Not integers {0} and {1}'.format(old_pods_2d[old_row][3],new_pods_2d[new_row][3]))
    #Check for NEW pods that were MANUALLY rebooted
    for new_row2 in range(len(new_pods_2d)):
    	my_found = False
    	for old_row2 in range(len(old_pods_2d)):
            if old_pods_2d[old_row2][0] == new_pods_2d[new_row2][0]:
            	# ok we don't care for this one
            	my_found = True
    	if my_found == False:
            logger.debug('{0} was manually rebooted'.format(new_pods_2d[new_row2][0]))
            if len(new_pods_2d[new_row2]) > 4 and new_pods_2d[new_row2][3].isdigit() and int(new_pods_2d[new_row2][3]) > 0 :
            	# we have a reboot
            	count_reboots += int(new_pods_2d[new_row2][3])
 
            	#Send message with updated timesheet
            	calculate_timesheet(new_pods_2d[new_row2][0],new_pods_2d[new_row2][3],current_time,new_pods_2d[new_row2][4])
    #To save the NEW Reboots to pickle database file
	set_pickle_data(my_global_dict['reboot_DB_pick_file'] ,new_pods_2d)
 
	#To update the timesheet DB pickle file
	set_pickle_data(my_global_dict['time_DB_pick_file'],timesheet_2d)
print(count_reboots)

