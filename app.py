# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client

# Set environment variables for your credentials
# Read more at http://twil.io/secure

account_sid = "ACc1ba0a48cb0ddae6c72c6146492d5bd9"
auth_token = "c7401b79e78fbbc397d89acb65e0ebe6"
client = Client(account_sid, auth_token)

call = client.calls.create(
  url="http://demo.twilio.com/docs/voice.xml",
  to="+918923834362",
  from_="+13613493717"
)

print(call.sid)