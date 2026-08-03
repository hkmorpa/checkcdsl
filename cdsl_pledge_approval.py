from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.chrome.options import Options  # Import Chrome options
import threading
import time
import sys
import re
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from get_otp import get_otp

# Create a lock to synchronize access to the file
file_lock = threading.Lock()
status_file = r"C:\checkcdsl\status.txt"

# Caps how many Chrome sessions run at once, regardless of how many threads are started
max_threads = 10
browser_semaphore = threading.Semaphore(max_threads)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    "./nirmalbang-6168910b93f4.json", scope
)
# Authenticate with the Google Sheets API
gc = gspread.authorize(credentials)
# Open the Google Sheet by its title
sheet_title = "checkcdsl"
print ("read_sheet called")
spreadsheet = gc.open(sheet_title)
worksheet_list = spreadsheet.worksheets()
global worksheet

def find_header_row(data):
    # Locates the row whose column A cell is exactly "PAN" - client rows start right after it
    for idx, row in enumerate(data):
        if row and row[0].strip().upper() == "PAN":
            return idx
    return None

def write_status(pan, status):
    data = worksheet.get_all_values()
    header_row = find_header_row(data)
    start_row = header_row + 1 if header_row is not None else 2
    for row in range(start_row, len(data)):
        if pan in data[row][0].strip():
            worksheet.update_cell(row + 1, 2, status)
            return
    print("write_status::PAN not found, MAJOR ERROR")

def approve_pledge(pan_number,email):
    # Blocks here until fewer than max_threads Chrome sessions are running
    browser_semaphore.acquire()
    try:
        # Create a new instance of the Chrome driver
        print("approve_pledge::PAN to be processed is ", pan_number, email)
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Add headless argument

        driver = webdriver.Chrome(options=chrome_options)  # Use the options

        try:
            # Open a website
            driver.get("https://www.cdslindia.com/Authentication/OTP.aspx")
            time.sleep(2)

            # ID of the first window
            cdslindia = driver.current_window_handle


            # Input value
            pan_input = driver.find_element(By.NAME, "txtpan")
            pan_input.send_keys(pan_number)

            # JavaScript snippet for obscured button
            button_element = driver.find_element(By.NAME, "btnSubmit")
            driver.execute_script("arguments[0].click();", button_element)
            time.sleep(2)

            # To solve unexpectedAlertPresentException:
            try:
                # Click checkbox
                # JavaScript snippet for obscured checkbox
                checkbox_element = driver.find_element(By.NAME, "grdvw$ctl01$chkall")
                driver.execute_script("arguments[0].click();", checkbox_element)

            except UnexpectedAlertPresentException:
                print("session had expired. Restarting...")
                return 2
            except :
                if "Margin pledge set up is not present for input" in driver.page_source:
                    print("HKG Margin pledge set up is not present for input:", pan_number)
                    write_status(pan_number, "nopledge")
                    return 3
                # in case of other exception
                return 2

            # Obtain OTP
            # JavaScript snippet for obscured button
            button_element1 = driver.find_element(By.NAME, "Button1")
            driver.execute_script("arguments[0].click();", button_element1)
            time.sleep(120)

            # Input OTP2:
            OTP1 = get_otp(email)
            print("OTP used is", OTP1)

            try:
                # Entering OTP:
                # JavaScript snippet for obscured entry
                entry = driver.find_element(By.NAME, "txttpinID")
                driver.execute_script("arguments[0].value = arguments[1];", entry, OTP1)
                time.sleep(2)

                # Submit final:-
                button2 = driver.find_element(By.NAME, "ButtonOTP")
                driver.execute_script("arguments[0].click();", button2)


                # Switch to the alert
                alert = driver.switch_to.alert

                # Accept the alert (click the "OK" button)
                alert.accept()
            except:
                print("Error while entering OTP...")

            time.sleep(2)
            return 1
        finally:
            # Close the browser on every exit path, including the return 2/3 branches above
            driver.quit()
    finally:
        browser_semaphore.release()

def process_pledge(pan,email):   

    print("process_pledge::PAN to be processed is", pan)
    ret_value = approve_pledge(pan,email)

    if(ret_value == 1): #pledge approved
        print("Processing is complete for Pan Number: ", pan)
    if(ret_value == 2): #session timeout
        while(1):
            ret_value = approve_pledge(pan,email.strip())
            if(ret_value == 2):
                continue
            else:
                print("Either approved or no pledge for Pan Number: ", pan)
                break
       

threads = []
# (worksheet, header_row) pairs - kept so we can re-scan each worksheet's client
# rows after all threads finish, to check the "everyone is nopledge" condition
worksheet_bounds = []

for worksheet in worksheet_list:
    # Read data from the Google Sheet
    data = worksheet.get_all_values()

    header_row = find_header_row(data)
    if header_row is None:
        print("No 'PAN' header found in worksheet:", worksheet.title, "- skipping")
        continue
    worksheet_bounds.append((worksheet, header_row))

    pan_start = header_row + 1
    while pan_start < len(data):      #Handles PAN till ENDPAN
        pan = data[pan_start][0].strip()
        if pan.upper() == "ENDPAN":
            break
        email = data[pan_start][3].strip().lower()
        status = data[pan_start][1].strip().lower()
        pan_start = pan_start + 1
        print("PAN to be processed is" , pan, email, status)
        if "nopledge" in status:
            print("Pledge not available for ",pan)
            continue
        # Thread starts immediately but blocks inside approve_pledge() until a
        # browser slot frees up (browser_semaphore caps it at max_threads)
        thread = threading.Thread(target=process_pledge, args=(pan, email))
        threads.append(thread)
        thread.start()
        print("Thread started with ",pan.strip(),email.strip())

# Wait for all threads to finish
for thread in threads:
    thread.join()

# If every client in a worksheet ended up "nopledge", reset them all to "EMPTY"
# so the next run rechecks everyone fresh instead of skipping them forever.
for worksheet, header_row in worksheet_bounds:
    data = worksheet.get_all_values()
    pan_start = header_row + 1
    client_rows = []
    while pan_start < len(data):
        pan = data[pan_start][0].strip()
        if pan.upper() == "ENDPAN":
            break
        client_rows.append(pan_start)
        pan_start += 1

    if client_rows and all("nopledge" in data[row][1].strip().lower() for row in client_rows):
        print("All clients are nopledge in worksheet", worksheet.title, "- resetting status to EMPTY")
        for i, row in enumerate(client_rows):
            worksheet.update_cell(row + 1, 2, "EMPTY")
            if (i + 1) % 30 == 0:
                time.sleep(60)

print("All threads have finished.")
