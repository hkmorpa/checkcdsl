from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.chrome.options import Options  # Import Chrome options
from tkinter import *
from tkinter import ttk
import threading
import time
import sys
import re
from get_otp import get_otp

# Create a lock to synchronize access to the file
file_lock = threading.Lock()
status_file = "C:\checkcdsl\status.txt"

def write_status(status):
    with file_lock:
        with open(status_file, "a") as file:
            file.write(status + "\n")

def pan_in_status(pan):
    try:
        with open(status_file, 'r') as file:
            file_contents = file.read()
            pan_matches = re.findall(pan, file_contents)
            return len(pan_matches)
    except:
        file = open(status_file, "w+")
        return 0
        

def approve_pledge(pan_number,email):   
    # Create a new instance of the Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Add headless argument

    driver = webdriver.Chrome(options=chrome_options)  # Use the options

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
        driver.quit()
        return 2
    except :
        if "Margin pledge set up is not present for input" in driver.page_source:
            print("HKG Margin pledge set up is not present for input:", pan_number)
            write_status(pan_number + " " + email)
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
    # Close the browser
    driver.quit()
    return 1

def process_pledge(pan_number,email):   
    print("PAN",pan_number)
    ret_value = approve_pledge(pan_number,email.strip())

    if(ret_value == 1): #pledge approved
        print("Processing is complete for Pan Number: ", pan_number)
    if(ret_value == 2): #session timeout
        while(1):
            ret_value = approve_pledge(pan_number,email.strip())
            if(ret_value == 2):
                continue
            else:
                print("Either approved or no pledge for Pan Number: ", pan_number)
                break
       

threads = []
max_threads = 20
thread_count = 0
with open("C:\checkcdsl\pan_email.txt", 'r') as file:
    for line in file:
        #skip processed PAN numbers
        print("Line is HKG",line)
        pan, email = line.split()
        if pan_in_status(pan) > 0:
            print("Pledge not available for ",pan)
            continue
        thread = threading.Thread(target=process_pledge, args=(pan.strip(),email.strip()))
        threads.append(thread)
        thread.start()
        print("Thread started with ",pan.strip(),email.strip())
        thread_count = thread_count + 1
        if thread_count >= max_threads:
            break
# Wait for all threads to finish
for thread in threads:
    thread.join()

if len(threads) == 0:
    file = open(status_file, "w+")

print("All threads have finished.")
