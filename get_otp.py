import imaplib
import email
from email.header import decode_header

def get_otp(email_arg):
    # Connect to the IMAP server
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    #mail.login("allclientshkg@gmail.com", "bzpsxfoczisgxqns")
    mail.login("allclientshkg@gmail.com", "dieturnktsjpixsj")

    # Select a mailbox (e.g., "INBOX")
    mailbox = "INBOX"
    mail.select(mailbox)

    # Search for unread emails
    status, email_ids = mail.search(None, "ALL")
    email_ids = email_ids[0].split()
    ret_val = "0"

    #Check if email is seen:
    i = 1
    while i < 100:
        email_id = email_ids[-i]
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        # Decode the subject
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding is not None else "utf-8")

        # Print email details
        print("From:", msg["From"])
        print("To:", msg["To"])
        print("Subject:", subject)
        print("Date:", msg["Date"])
        if(email_arg.lower() == msg["To"].strip().lower()):
            #Body of the mail from which we need to get the OTP:
            body = msg.get_payload(decode=True).decode()
            lines = body.splitlines()
            if len(lines) >= 8:
                eighth_line = lines[7]  # Lines are 0-indexed
                words = eighth_line.split()
                if len(words) >= 24:
                    twentyfourth_word = words[19]  # Words are 0-indexed
                    if len(twentyfourth_word) >= 12:
                        OTP = twentyfourth_word[0:4]  # Characters are 0-indexed
                        print("OTP:", OTP)
                        ret_val = OTP
            break
        i = i + 1
    # Logout and close the connection
    mail.logout()
    return ret_val
