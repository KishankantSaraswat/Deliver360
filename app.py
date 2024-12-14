import os
from twilio.rest import Client

# Securely store your credentials
account_sid = "ACc1ba0a48cb0ddae6c72c6146492d5bd9"
auth_token = "6336806d01669c81599de47f229d04af"
client = Client(account_sid, auth_token)

try:
    call = client.calls.create(
        url="http://demo.twilio.com/docs/voice.xml",
        to="+918923834362",
        from_="+13613493717"
    )
    print(f"Emergency call initiated. Call SID: {call.sid}")
except Exception as e:
    print(f"Error occurred: {e}")
