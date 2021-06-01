Runs a backup operation for data in the specified cloud service.

Usage:
  cloud-service-backup <service> <mode> <args>...
  cloud-service-backup gmail (copy|sync) foo.bar@gmail.com
  cloud-service-backup google-drive (copy|sync) foo.bar@gmail.com
  cloud-service-backup google-photos (copy|sync) foo.bar@gmail.com <year>
  cloud-service-backup dropbox (copy|sync) foo.bar@gmail.com
  cloud-service-backup github (copy|sync) foo.bar
  cloud-service-backup bitbucket (copy|sync) foo.bar

Environment variables:
  BACKUPDATAD: Required. The directory into which backup data for
               all services will be saved and automatically organized.
  BACKUPCONFD: Required. The directory into which configuration data
               will be saved & organized.
  GOOGLE_OAUTH_CLIENT_ID:
               Optional. For Google services, if using a custom/personal
               OAuth app for auth tokens.
  GOOGLE_OAUTH_CLIENT_SECRET:
               Optional. Client secret for client ID above.
        
The <mode> argument can be either "copy" or "sync". While this may
means slightly different things for each service, in general it means:
  copy: Non-destructive copy from remote service to local disk.
        i.e. Copy new and modified files/data, don't remove anything.
  sync: Full one-way synchronization from remote service to local disk.
        i.e. Local will match remote files/data on completion.

"copy" mode is recommended for daily automated backups. "sync" mode is
recommended for less periodic and/or manual backups. This approach helps
protect against accidental or malicious deletion of files within a
cloud service. If this happens, a daily automated "copy" would preserve
those local files. A less periodic and/or manual "sync" could be run
when the state of your data in the cloud service is in a known good state.

Note: Each command should be run interactively the first time (for
authentication, etc.) and can be run unattended after that.
