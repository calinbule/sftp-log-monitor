## SFTP Log monitoring tool
- in the console-like area, the app will initially print the last 100 rows, then it continues scanning for new content
- when new content is added to the log file, the app will print all of that new content
- to keep track more easily of what's printed, the print batch number will be printed before the actual content. Ex: `<19.02.2025 13:10:04> Printing batch 1`
- also, beacause this is not quite real-time, a print timestamp will be prepended to every print. Ex: `<19.02.2025 13:10:04>`


#### Steps to install
1) clone this repo: `git clone https://github.com/calinbule/sftp-log-monitor.git`
2) rename the environment variables file: `mv sample.env .env`
3) in the .env file, change the variables if needed
- `LOG_MONITOR_PORT` is the port the app will expose
- `SLEEP_BETWEEN_LOG_CHECKS` represents the sleep times between polls to the log file that is currently being monitored
- `LOG_EXTENSIONS` contains a list, separated by comma (no spaces), of the file extensions in the remote SFTP directory, that you want to be considered as log
- `POUPLATE_DB` set to `true` if you want the one settings record, with your connection data, to be created, at database initalization (the data added via script will be visible and modifiable via the web Settings interface later); set to `false` if ypu wish to fill the data by hand, after you've started the application; if set to `true`, please be sure to also configure the `SFTP_HOSTNAME`, `SFTP_USERNAME`, `SFTP_PASSWORD`, `SFTP_PORT` and `SFTP_REMOTE_DIR` variables, with the appropiate values
4) build the container: `docker compose build`
5) run the container: `docker compose  up -d`



#### Instructions
1) access the app at `http://localhost:5000`; if you changed the port in the .env file, use that one in the url
2) go to `Settings` and configure credentials and the remote directory path where the logs are stored, in the SFTP location, and then `Save settings`
3) return to the index page, and you should see the top left dropdown list populated with the logs that are present in the remote location you configured in `Settings` (the app scans the directory for files with the .log extension and for all the files if finds, it removes the extension then adds them to the list)
4) press `Start`, to start monitoring the selected log file (it should work similarly to `fail -f log_file.txt, but over SFTP)
5) press `Pause` to pause the monitoring process, or `Stop` to close it


### Notes
- if you switch page, or hit refresh, the monitorin process stops

