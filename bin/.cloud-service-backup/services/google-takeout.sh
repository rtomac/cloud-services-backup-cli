function svc_google_takeout_help {
    cat <<EOF
Backs up files from all Google Takeout archives that are
created and saved into Google Drive (one of the options
Google Takeout provides). Uses rclone with a 'drive'
remote to download the archive files, and then coalesces
all files from all archives over time into a single backup 
folder.

The idea here is to allow a user to manually schedule Takeout
archives but automate it all the rest of the way. Google allows
you to schedule a year's worth of archives, six archives every
two months.

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username>
        Downloads archive files and syncs their contents
        into the backup dir.
  sync <google_username>
        Downloads archive files and syncs their contents
        into the backup dir. Will also remove any archive files
        locally that were cleaned up in Google Drive (but will
        never remove backed up files that were in those archives).

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://rclone.org/drive/#making-your-own-client-id
EOF
}

function svc_google_takeout_init {
    google_username=${1:?google_username arg required}

    user_slug=${google_username//[^[:alnum:]]/_}
    user_backupd=${CLOUD_BACKUP_DATAD}/google_takeout/${user_slug}
    user_backupd_archives=${user_backupd}/.archives
    rclone_remote=google_drive+${user_slug}

    mkdir -p "${user_backupd}"

    echo "Using rclone remote ${rclone_remote} with config at ${RCLONE_CONFIG}"
    echo "Backing up to ${user_backupd}"
}

function svc_google_takeout_setup {
    svc_google_drive_setup
}

function svc_google_takeout_copy { svc_google_takeout_backup; }
function svc_google_takeout_sync { svc_google_takeout_backup; }
function svc_google_takeout_backup {
    if ! rclone_has_remote "${rclone_remote}"; then
        svc_google_takeout_setup
    fi

    echo "Starting rclone ${subcommand} to download/sync archives..."
    rclone_x ${subcommand} --stats-log-level NOTICE --stats 1m "${rclone_remote}":/Takeout/ "${user_backupd_archives}"

    echo "Extracting archives..."
    _svc_google_takeout_extract_archives
    _svc_google_takeout_extract_cleanup

    echo "Backing up takeout files..."
    _svc_google_takeout_sync_archives
}

function _svc_google_takeout_extract_archives {
    for file in "${user_backupd_archives}"/*.tgz "${user_backupd_archives}"/*.zip; do
        [ -e "$file" ] || continue  # skip literal matches
        fname="$(basename "$file")"
        dir="${file%.*}"

        if [ ! -d "$dir" ]; then
            mkdir "$dir"
            echo "Extracting $fname..."
            if [[ $file == *.tgz ]]; then
                tar -xzf "$file" -C "$dir"
            elif [[ $file == *.zip ]]; then
                unzip -q "$file" -d "$dir"
            else
                echo "Can't extract $fname"
                exit 1
            fi
        else
            echo "Skipping $fname, folder already exists"
        fi
    done
}

function _svc_google_takeout_extract_cleanup {
    for dir in "$user_backupd_archives"/*/; do
        [ -d "$dir" ] || continue  # skip if not a directory
        dname="$(basename "$dir")"
        if [ ! -f "$user_backupd_archives/$dname".* ]; then
            echo "Deleting folder $dname, no corresponding archive found"
            rm -rf "$dir"
        fi
    done
}

function _svc_google_takeout_sync_archives {
    for dir in "$user_backupd_archives"/*/; do
        [ -d "$dir" ] || continue  # skip if not a directory
        dname="$(basename "$dir")"
        echo "Syncronizing files from $dname..."
        rsync --archive --update --verbose "$dir/Takeout/" "$user_backupd"
    done
}
