## Notifier
### Simple python class for sending emails

```python
mail_dict = {
    "sender": "sender@mail.com",
    "recipients": ["recipient1@person.com", 
                   "recipient2@person.com", 
                   "recipient3@person.com"],
    "subject": "Yo, sup",
    "body": "<h2>Body works</h2>",
}

email = Emailer(mail_dict)
email.send_mail()
```
