#####################################################################################
#                          Database Backup Application                              #
#                      Automates backup of SQL databases                            #
#####################################################################################
# Developer: Oriname Agbi                                                           #
# Version: 1.0.0                                                                    #
# Date: 2024                                                                        #
#####################################################################################
# Description:                                                                      #
# This application is designed to automate the process of backing up SQL            #
# databases. It supports multiple database systems and provides features such       #
# as scheduling backups, database validation, compressing backup files, and logging.#
#####################################################################################

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
import pyodbc
import winreg as reg
import win32com.client
import os
import sys
import datetime
import threading
import logging
import re
import time
import glob
#import sv_ttk
import configparser
from cryptography.fernet import Fernet
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Setup logging
logging.basicConfig(filename='database_backup.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def encrypt_string(plain_text, key):
    """Encrypt a string using Fernet encryption."""
    fernet = Fernet(key)
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_string(encrypted_text, key):
    """Decrypt an encrypted string using Fernet encryption."""
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_text.encode()).decode()

def is_valid_time(time_str):
    """Check if the time string is in 24-hour format HH:MM."""
    if re.match(r'^[0-2][0-9]:[0-5][0-9]$', time_str):
        hour, minute = map(int, time_str.split(':'))
        return 0 <= hour <= 23 and 0 <= minute <= 59
    return False

def is_positive_integer(value):
    """Check if the provided string represents a positive integer."""
    try:
        return int(value) > 0
    except ValueError:
        return False


class DatabaseBackupApp:
    def __init__(self, master):
        self.master = master
        master.title("Database Backup App")
        self.stop_requested = threading.Event()
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.encryption_key = self.config['Security']['Key'].encode()

        # Create a menu bar
        self.menu_bar = tk.Menu(master)
        master.config(menu=self.menu_bar)

        # Create "Help" menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about_info)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        #sv_ttk.set_theme("light")
    

        #Scheduler 

        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # UI components
        tk.Label(master, text="Database Name:").grid(row=0, column=0, sticky=tk.W)
        self.database_entry = tk.Entry(master)
        self.database_entry.grid(row=0, column=1)

        tk.Label(master, text="Username:").grid(row=1, column=0, sticky=tk.W)
        self.username_entry = tk.Entry(master)
        self.username_entry.grid(row=1, column=1)

        tk.Label(master, text="Server Name:").grid(row=2, column=0, sticky=tk.W)
        self.server_entry = tk.Entry(master)
        self.server_entry.grid(row=2, column=1)

        tk.Label(master, text="Password:").grid(row=3, column=0, sticky=tk.W)
        self.password_entry = tk.Entry(master, show="*")
        self.password_entry.grid(row=3, column=1)

        tk.Label(master, text="Backup Directory:").grid(row=4, column=0, sticky=tk.W)
        self.backup_dir_entry = tk.Entry(master)
        self.backup_dir_entry.grid(row=4, column=1)
        tk.Button(master, text="Browse", command=self.browse_backup_dir).grid(row=4, column=2, padx=5, pady=5, sticky=tk.E)

        tk.Label(master, text="Backup Schedule (HH:MM):").grid(row=5, column=0, sticky=tk.W)
        self.schedule_entry = tk.Entry(master)
        self.schedule_entry.grid(row=5, column=1)

        # Manual Backup Button - Positioned next to the Backup Directory
        #self.full_backup_button = tk.Button(master, text="Manual Backup", command=lambda: self.initiate_backup('full', 'manual'))
        self.full_backup_button = tk.Button(self.master, text="Manual Backup", command=lambda: self.initiate_backup('full', 'manual'))
        self.full_backup_button.grid(row=4, column=3, padx=5, sticky=tk.W)

        tk.Label(master, text="Full Backup Frequency (Days):").grid(row=6, column=0, sticky=tk.W)
        self.full_backup_frequency_entry = tk.Entry(master)
        self.full_backup_frequency_entry.grid(row=6, column=1)
        self.full_backup_frequency_entry.insert(0, "7")  # Default value


        # Test Connection Button - Positioned below Username and Server Name
        self.test_connection_button = tk.Button(master, text="Test Connection", command=self.test_connection)
        self.test_connection_button.grid(row=1, column=2, columnspan=2, padx=5, pady=5)

        # Save and Edit Schedule Buttons - Grouped together below the schedule entry
        self.save_button = tk.Button(master, text="Save Schedule", command=self.save_schedule_and_lock)
        self.save_button.grid(row=5, column=2, padx=5, pady=5, sticky=tk.E)

        self.edit_button = tk.Button(master, text="Edit / Stop", command=self.unlock_schedule_for_editing)
        self.edit_button.grid(row=5, column=3, padx=5, pady=5, sticky=tk.W)

        # Log Text Widget - Styled with black background and white text
        self.log_text = tk.Text(master, height=15, width=70, bg='black', fg='white', font=('Courier', 10))
        self.log_text.grid(row=7, column=0, columnspan=4)
        self.log("Application started....")

        self.full_backup_frequency_entry.delete(0, tk.END)  # Clear existing value
        self.full_backup_frequency_entry.insert(0, self.config.get('Backup', 'Frequency', fallback="7"))  # Load or default to 7


        # Configure the Text widget to use a monospaced font for better alignment
        self.log_text.configure(font=('Courier', 10))

        # Load encrypted credentials if they exist
        self.load_credentials()

        #Automatically save schedule if credentials are available
        if self.are_credentials_complete():
            self.save_schedule_and_lock(context='auto')

                
        # Configure the scheduler with any saved schedule
        self.configure_scheduler()



        master.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def show_about_info(self):
        """Display information about the app."""
        title = "About Database Backup App"
        message = ("Database Backup App Version 1.0\n"
                "Author: Oriname Agbi\n"
                "Date: 2024-03-18\n\n"
                "This application automates the process of SQL database backups, including scheduling.")
        messagebox.showinfo(title, message)


    def configure_scheduler(self):
        """Configure the scheduler with the user-defined schedule."""
        schedule_time = self.schedule_entry.get().strip()
        if schedule_time:
            hour, minute = schedule_time.split(':')
            # Remove existing jobs to avoid duplicates
            self.scheduler.remove_all_jobs()
            # Add new job with the updated schedule
            self.scheduler.add_job(self.initiate_scheduled_backup, CronTrigger(hour=int(hour), minute=int(minute)),
                                id="database_backup", replace_existing=True)
            logging.info(f"Scheduled backup at {hour}:{minute} daily.")
            
    def load_credentials(self):
        """Loads and decrypts database credentials from the config file."""
        try:
            self.database_entry.delete(0, tk.END)
            self.database_entry.insert(0, self.config.get('Database', 'Name', fallback=''))
            
            self.server_entry.delete(0, tk.END)
            self.server_entry.insert(0, self.config.get('Database', 'Server', fallback=''))
            
            self.backup_dir_entry.delete(0, tk.END)
            self.backup_dir_entry.insert(0, self.config.get('Backup', 'Directory', fallback=''))
            
            encrypted_username = self.config.get('Database', 'Username', fallback=None)
            encrypted_password = self.config.get('Database', 'Password', fallback=None)
            
            if encrypted_username and encrypted_password:
                self.username_entry.delete(0, tk.END)
                self.username_entry.insert(0, decrypt_string(encrypted_username, self.encryption_key))
                self.password_entry.delete(0, tk.END)
                self.password_entry.insert(0, decrypt_string(encrypted_password, self.encryption_key))
            
            self.schedule_entry.delete(0, tk.END)
            self.schedule_entry.insert(0, self.config.get('Backup', 'Schedule', fallback='00:00'))
            
            self.full_backup_frequency_entry.delete(0, tk.END)
            self.full_backup_frequency_entry.insert(0, self.config.get('Backup', 'Frequency', fallback='7'))
        except Exception as e:
            self.log(f"Error loading credentials: {e}", level="ERROR")

    def save_credentials(self):
        """Encrypts and saves database credentials to the config file."""
        try:
            self.config['Database'] = {
                'Name': self.database_entry.get(),
                'Server': self.server_entry.get(),
                'Username': encrypt_string(self.username_entry.get(), self.encryption_key),
                'Password': encrypt_string(self.password_entry.get(), self.encryption_key)
            }
            self.config['Backup'] = {
                'Directory': self.backup_dir_entry.get(),
                'Schedule': self.schedule_entry.get(),
                'Frequency': self.full_backup_frequency_entry.get()
            }
            with open('config.ini', 'w') as configfile:
                self.config.write(configfile)
            self.log("Credentials saved successfully.")
        except Exception as e:
            self.log(f"Error saving credentials: {e}", level="ERROR")

    def are_credentials_complete(self):
        """Check if all necessary credentials are filled."""
        return all([
            self.database_entry.get(),
            self.server_entry.get(),
            self.username_entry.get(),
            self.password_entry.get(),
            self.backup_dir_entry.get(),
            self.schedule_entry.get(),
            self.full_backup_frequency_entry.get()
        ])

    def save_schedule_and_lock(self, context = 'scheduled'):
        """Saves the user-defined backup schedule and backup frequency, then locks the input fields and buttons."""
        # Collect all field values
        inputs = {
            'backup_schedule': self.schedule_entry.get().strip(),
            'backup_frequency': self.full_backup_frequency_entry.get().strip(),
            'database_name': self.database_entry.get().strip(),
            'username': self.username_entry.get().strip(),
            'password': self.password_entry.get().strip(),
            'server_name': self.server_entry.get().strip(),
            'backup_dir': self.backup_dir_entry.get().strip(),
        }

        # Save credentials
        self.save_credentials()

        # Check if any of the fields are empty or invalid
        if not all(inputs.values()) or not is_positive_integer(inputs['backup_frequency']) or not is_valid_time(inputs['backup_schedule']):
            messagebox.showwarning("Invalid Settings", "Please ensure all fields are filled out, the backup frequency is a positive number, and the schedule is in 24-hour HH:MM format.")
            return

        # Proceed with saving schedule and frequency
        self.config.set('Backup', 'Schedule', inputs['backup_schedule'])
        self.config.set('Backup', 'Frequency', inputs['backup_frequency'])
        self.log(f"Backup has been scheduled for {(inputs['backup_schedule'])} daily.")
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        messagebox.showinfo("Settings Saved", "Your backup schedule and frequency have been saved.")

        # Disable UI components to lock the settings
        for entry in [self.schedule_entry, self.full_backup_frequency_entry, self.database_entry, self.username_entry, self.password_entry, self.server_entry, self.backup_dir_entry]:
            entry.config(state='disabled')

        # Also disable all buttons
        for button in [self.save_button, self.full_backup_button]:
            button.config(state='disabled')

        # Apply the new schedule
        self.stop_requested.clear()  # Clear the stop signal to allow operations to resume
        self.configure_scheduler()

    def on_close(self):
        """Shuts down the scheduler cleanly when the application is closed."""
        self.scheduler.shutdown()
        self.master.destroy()

    def unlock_schedule_for_editing(self):
        self.stop_requested.set()  # Signal to stop all operations
        # Stop or remove any scheduled backup jobs
        try:
            self.scheduler.remove_all_jobs()  # This removes all jobs, ensuring no backups are scheduled
            logging.info("All scheduled backup jobs have been stopped.")
        except Exception as e:
            logging.error(f"Error stopping scheduled backup jobs: {e}")

        # Re-enable the input fields and buttons for editing
        for entry in [self.schedule_entry, self.full_backup_frequency_entry, self.database_entry, self.username_entry, self.password_entry, self.server_entry, self.backup_dir_entry]:
            entry.config(state='normal')

        # Re-enable all buttons
        for button in [self.save_button, self.test_connection_button, self.full_backup_button]:
            button.config(state='normal')

        self.log("Backup schedule editing is unlocked. All scheduled jobs are stopped.", level="WARNING")
    
    def test_connection(self):
        """Tests the database connection using the provided credentials and logs the outcome."""
        server = self.server_entry.get()
        database = self.database_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        try:
            with pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};', timeout=10) as conn:
                messagebox.showinfo("Connection Test", "Connection to the database was successful.")
                self.log("Connection to the database was successful.")
        except Exception as e:
            messagebox.showerror("Connection Test", f"Failed to connect to the database:\n{e}")
            self.log(f"Failed to connect to the database: {e}")

    def load_credentials(self):
        """Loads and decrypts database credentials from the config file."""
        encrypted_username = self.config.get('Database', 'Username', fallback=None)
        encrypted_password = self.config.get('Database', 'Password', fallback=None)
        if encrypted_username and encrypted_password:
            self.username_entry.insert(0, decrypt_string(encrypted_username, self.encryption_key))
            self.password_entry.insert(0, decrypt_string(encrypted_password, self.encryption_key))

    def browse_backup_dir(self):
        """Opens a dialog for selecting a backup directory."""
        backup_dir = filedialog.askdirectory()
        if backup_dir:
            self.backup_dir_entry.delete(0, tk.END)
            self.backup_dir_entry.insert(0, backup_dir)

    def initiate_scheduled_backup(self):
        """Determines the type of backup to perform based on conditions and initiates it."""
        now = datetime.datetime.now()
        backup_type = 'differential'  # Start with the assumption of doing a differential backup

        # First, check if a valid full backup exists in the directory.
        if not self.has_existing_full_backup(self.database_entry.get()):
            logging.info("No full backup found in directory. Performing full backup instead.")
            backup_type = 'full'
        else:
            # If a full backup exists, check the schedule and last full backup date to decide.
            last_full_backup_date_str = self.config.get('Backup', 'LastFullBackupDate', fallback=None)
            if last_full_backup_date_str:
                last_full_backup_date = datetime.datetime.strptime(last_full_backup_date_str, '%Y%m%d')
                days_since_last_full = (now - last_full_backup_date).days
                try:
                    backup_frequency = int(self.full_backup_frequency_entry.get())  # Get the user-defined backup frequency
                except ValueError:
                    messagebox.showwarning("Invalid Frequency", "Please enter a valid number for the backup frequency.")
                    return

                if days_since_last_full >= backup_frequency:
                    logging.info(f"More than {backup_frequency} days since last full backup. Performing full backup.")
                    backup_type = 'full'
            else:
                # If there's no record of the last full backup date, default to doing a full backup
                logging.info("No record of last full backup date found. Performing full backup.")
                backup_type = 'full'

        self.initiate_backup(backup_type)


    def initiate_backup(self, backup_type, context = 'scheduled'):
        # Clear the stop signal only for manual backups
        if context == 'manual':
            self.stop_requested.clear()
        logging.info(f"Initiating {context} {backup_type} backup process.")

        def backup_logic():
            database_name = self.database_entry.get()
            # Check with SQL Server before deciding backup type
            if backup_type == 'differential' and not self.validate_last_full_backup_with_sql_server(database_name):
                logging.info("SQL Server does not recognize the last full backup. Performing full backup before differential.")
                self.perform_backup('full', context = context)
                time.sleep(2)  # Ensure there's a slight delay to avoid filename timestamp clash

            if backup_type == 'differential':
                # Attempt differential backup and check for success
                differential_success = self.perform_backup('differential')
                if not differential_success:
                    logging.error("Differential backup failed after 3 attempts. Proceeding with full backup.")
                    self.perform_backup('full', context = context)
            else:
                # If not a differential backup, or after handling differential failure, perform backup as initially requested
                self.perform_backup(backup_type, context = context)

        backup_thread = threading.Thread(target=backup_logic, daemon=True)
        backup_thread.start()

    def perform_backup(self, backup_type, context = 'scheduled'):
        logging.info(f"{context.capitalize()} {backup_type} backup process is starting.")

        server = self.server_entry.get()
        database = self.database_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        backup_dir = self.backup_dir_entry.get()
        
        # Generate backup file path with a timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        backup_filename = f"{database}_{backup_type}_{timestamp}.bak"
        backup_file_path = os.path.join(backup_dir, backup_filename)
        
        retry_count = 9
        retry_delay = 60  # seconds for retries if backup fails
        success = False  # Flag to indicate if backup was successful
        for attempt in range(retry_count):
            if self.stop_requested.is_set():
                logging.info("Stop requested, aborting backup.")
                return False  # Early exit if stop has been requested
            
            try:
                # Execute the backup using SQL command
                with pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};', autocommit=True, timeout=10) as conn:
                    cursor = conn.cursor()
                    if backup_type == 'full':
                        sql_backup = f"BACKUP DATABASE [{database}] TO DISK = N'{backup_file_path}' WITH INIT;"
                    elif backup_type == 'differential':
                        sql_backup = f"BACKUP DATABASE [{database}] TO DISK = N'{backup_file_path}' WITH DIFFERENTIAL, INIT;"
                    cursor.execute(sql_backup)
                    cursor.commit()
                
                # Backup command executed successfully, validate the backup file
                if self.validate_backup(backup_file_path):
                    # If validation passes, update configuration and cleanup
                    self.update_backup_configuration(backup_type, backup_file_path, timestamp)
                    self.cleanup_old_backups()
                    self.log(f"{context.capitalize()} {backup_type} backup completed successfully: {backup_file_path}", level="INFO")

                    success = True  # Set success to True as backup was successful
                    break  # Break out of the loop on success
                else:
                    # If validation fails, log as an error and trigger a retry
                    raise Exception(f"{backup_type.capitalize()} backup file validation failed: {backup_file_path}")
            except Exception as e:
                self.log(f"Attempt {attempt + 1} of {context} {backup_type} backup failed: {e}", level="ERROR")
                if attempt < retry_count - 1:
                    self.log(f"Retrying in {retry_delay} seconds...", level="WARNING")
                    time.sleep(retry_delay)

        # If the backup was not successful after all retries, log an error message
        if not success:
            self.log(f"All attempts to perform {context} {backup_type} backup have failed. Please check the log for details.", level="ERROR")
        
        # Return the success status of the backup operation
        return success 

    def has_existing_full_backup(self, database):
        """Check if a full backup exists for the specified database, considering potential external changes."""
        try:
            backup_dir = self.backup_dir_entry.get()
            full_backup_files = [file for file in os.listdir(backup_dir) if 'full' in file and database in file]
            if full_backup_files:
                # Sort files by modification time in descending order
                full_backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
                most_recent_full = full_backup_files[0]
                logging.info(f"Found existing full backup for database {database}: {most_recent_full}")
                return True
            else:
                logging.info(f"No existing full backup found for database {database}.")
                return False
        except Exception as e:
            logging.error(f"Failed to check for existing full backup for database {database}: {e}")
            # In case of error, conservatively assume no valid full backup exists to avoid potential data loss
            return False

    def should_do_full_backup(self):
        """Determines if it's time to perform a full backup based on the elapsed time since the last full backup."""
        last_full_backup_str = self.config.get('Backup', 'LastFullBackupDate', fallback=None)
        if last_full_backup_str is None:
            # If there's no record of the last full backup, do a full backup
            return True

        # Convert the last full backup date from string to datetime
        last_full_backup_date = datetime.datetime.strptime(last_full_backup_str, '%Y-%m-%d')
        # Calculate the number of days since the last full backup
        days_since_last_full = (datetime.datetime.now() - last_full_backup_date).days

        # If more than 7 days have passed since the last full backup, return True
        return days_since_last_full > 7
    
    def validate_last_full_backup_with_sql_server(self, database_name):
        try:
            connection_string = f'DRIVER={{SQL Server}};SERVER={self.server_entry.get()};DATABASE={database_name};UID={self.username_entry.get()};PWD={self.password_entry.get()};'
            with pyodbc.connect(connection_string, timeout=10) as conn:
                cursor = conn.cursor()
                query = """
                    SELECT TOP 1 *
                    FROM msdb.dbo.backupset
                    WHERE database_name = ?
                    AND type = 'D'
                    ORDER BY backup_finish_date DESC
                """
                cursor.execute(query, database_name)
                result = cursor.fetchone()
                if result:
                    logging.info(f"Valid last full backup for {database_name} is recognized by SQL Server.")
                    return True
                else:
                    logging.warning(f"No valid last full backup for {database_name} recognized by SQL Server.")
                    return False
        except Exception as e:
            logging.error(f"Error checking last full backup with SQL Server: {e}")
            return False

    def cleanup_old_backups(self):
        try:
            """Keeps only the most recent backups, deletes the rest, with separate handling for full and differential backups."""
            backup_files = glob.glob(os.path.join(self.backup_dir_entry.get(), '*.bak'))

            # Handle full backups
            full_backups = [file for file in backup_files if 'full' in file]
            full_backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            for old_backup in full_backups[2:]:  # Adjust the number as needed
                os.remove(old_backup)
                logging.info(f"Old full backup deleted: {old_backup}")

            # Handle differential backups
            differential_backups = [file for file in backup_files if 'differential' in file]
            differential_backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            for old_backup in differential_backups[2:]:  # Keep only the two most recent
                os.remove(old_backup)
                logging.info(f"Old differential backup deleted: {old_backup}")
                
        except PermissionError as e:
            error_message = f"Permission error encountered while trying to delete old backups: {e}"
            logging.error(error_message)
            self.log(error_message, level="ERROR")  # Log the error in the application's log area
            self.master.after(0, lambda: messagebox.showerror("Permission Error", error_message))
        # The lambda function ensures messagebox.showerror runs in the main thread, avoiding threading issues with Tkinter
        
        except Exception as e:
            general_error_message = f"General error encountered while trying to delete old backups: {e}"
            logging.error(general_error_message)
            self.log(general_error_message, level="ERROR")


    def execute_backup(self, backup_type, backup_file_path, server, database, username, password):
        """Executes the backup command to SQL Server."""
        try:
            with pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};', timeout=10) as conn:
                cursor = conn.cursor()
                sql_backup = ""
                if backup_type == 'full':
                    sql_backup = f"BACKUP DATABASE [{database}] TO DISK = N'{backup_file_path}' WITH INIT;"
                elif backup_type == 'differential':
                    sql_backup = f"BACKUP DATABASE [{database}] TO DISK = N'{backup_file_path}' WITH DIFFERENTIAL, INIT;"
                cursor.execute(sql_backup)
                cursor.commit()
            self.log(f"{backup_type.capitalize()} backup completed successfully. Backup file: {backup_file_path}")
        except Exception as e:
            logging.error(f"Backup failed: {e}")
            self.log(f"Backup failed: {e}")
        try:
        # Backup command execution logic
            if backup_type == 'full':
                # After a successful full backup, update the config
                self.config.set('Backup', 'LastFullBackupDate', datetime.datetime.now().strftime('%Y-%m-%d'))
                self.config.set('Backup', 'LastFullBackupFile', backup_file_path)
                with open('config.ini', 'w') as configfile:
                    self.config.write(configfile)
                logging.info(f"Configuration updated with the latest full backup details: {backup_file_path}")
        except Exception as e:
            logging.error(f"Backup failed: {e}")
        finally:
            self.enable_backup_buttons()

    def validate_backup(self, backup_file_path):
        if os.path.exists(backup_file_path) and os.path.getsize(backup_file_path) > 0:
            logging.info(f"Backup file validated successfully: {backup_file_path}")
            return True
        else:
            logging.error(f"Backup file validation failed or file is empty: {backup_file_path}")
            
            return False    
    
    def log(self, message, level="INFO"):
        """Safely logs a message with a timestamp, level, and color to the text widget and the log file from any thread."""
        def do_log():
            # Define colors and font weights for different levels
            styles = {
                "INFO": {"foreground": "green", "font": ("Helvetica", 10)},
                "WARNING": {"foreground": "orange", "font": ("Helvetica", 10, "bold")},
                "ERROR": {"foreground": "red", "font": ("Helvetica", 10, "bold")},
            }
            
            # Set the default style if the level is not recognized
            style = styles.get(level, styles["INFO"])

            # Get the current time and format it
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            formatted_message = f"{timestamp} - {level} - {message}\n\n"

            # Log to file without the timestamp to avoid duplication in the log file
            getattr(logging, level.lower(), logging.info)(message)

            # Ensure the widget is in a normal state for text insertion
            self.log_text.configure(state='normal')
            
            # Configure and apply the tag with the style for this level
            self.log_text.tag_configure(level, **style)
            self.log_text.insert(tk.END, formatted_message, level)
            
            # Scroll to the end of the log text
            self.log_text.see(tk.END)
            
            # Make the widget read-only again
            self.log_text.configure(state='disabled')
        
        # Schedule the do_log function to run in the main thread
        self.master.after(0, do_log)

    def update_backup_configuration(self, backup_type, backup_file_path, timestamp):
        if backup_type == 'full':
            self.config['Backup']['LastFullBackupFile'] = backup_file_path
            # Use just the date part for LastFullBackupDate
            self.config['Backup']['LastFullBackupDate'] = timestamp[:8]  # YYYYMMDD format
            with open('config.ini', 'w') as configfile:
                self.config.write(configfile)
            logging.info(f"Configuration updated successfully with {backup_type} backup details.")

    def log_backup_details(self, backup_type, backup_file_path):
        backup_size = os.path.getsize(backup_file_path) / (1024 * 1024)  # Convert size to MB
        logging.info(f"Completed {backup_type} backup: {backup_file_path}, Size: {backup_size:.2f} MB")

    def enable_backup_buttons(self):
        """Re-enables the full and differential backup buttons."""
        self.full_backup_button.config(state=tk.NORMAL)
        #self.differential_backup_button.config(state=tk.NORMAL)


def create_config():
    config = configparser.ConfigParser()
    config['Security'] = {'Key': Fernet.generate_key().decode()}
    config['Backup'] = {
        'LastFullBackupDate': '',  # Initialize with an empty date
        'LastFullBackupFile': '',  # Initialize with an empty path
        'Schedule': '00:00',  # Default backup schedule (HH:MM). Adjust as needed.
        'Frequency': '7',  # Default value for how many days between full backups
    }
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
    print("Configuration file created. Please edit 'config.ini' with your encrypted credentials, backup path, schedule, and frequency.")

def add_to_startup(file_path=""):
    if getattr(sys, 'frozen', False):
        # The application is frozen
        file_path = sys.executable
    else:
        # The application is not frozen
        # Change this bit to match where you store your data files:
        file_path = os.path.abspath(__file__)

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS)
        reg.SetValueEx(key, "DatabaseBackupApp", 0, reg.REG_SZ, file_path)
        reg.CloseKey(key)
        print("Successfully added to startup!")
    except WindowsError:
        print("Failed to add to startup!")

if __name__ == "__main__":
    if not os.path.exists('config.ini'):
        create_config()
    add_to_startup()  # Add this line
    root = tk.Tk()
    app = DatabaseBackupApp(root)
    root.mainloop()