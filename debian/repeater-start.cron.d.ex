#
# Regular cron jobs for the repeater-start package
#
0 4	* * *	root	[ -x /usr/bin/repeater-start_maintenance ] && /usr/bin/repeater-start_maintenance
