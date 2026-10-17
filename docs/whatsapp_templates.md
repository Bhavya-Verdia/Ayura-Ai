# WhatsApp setup

The app sends three kinds of WhatsApp message through Meta's **WhatsApp Cloud API**.
Each is a pre-approved *template*: a business may only start a conversation with one.
Nothing is sent until the steps below are done and `WHATSAPP_ENABLED=true`.

## 1. Accounts (one-time, done by the business owner)

1. Create or verify a **Meta Business** account (business.facebook.com). Business
   verification needs company documents; until it completes, Meta limits how many
   people you can message per day.
2. In **WhatsApp Manager**, add a phone number that is **not** already on the WhatsApp
   app (a new SIM or a landline that can receive an SMS or call for its code).
3. Set the display name ("Ayura AI") — Meta reviews it.
4. In **Business Settings › System users**, create a system user, give it the WhatsApp
   account, and generate a **permanent token** with `whatsapp_business_messaging` and
   `whatsapp_business_management`.
5. Copy the **Phone number ID** from WhatsApp Manager › API setup (it is an ID, not the
   number itself).

## 2. Templates to submit (WhatsApp Manager › Message templates)

Names must match exactly; they are read from `WHATSAPP_TEMPLATE_*` and default to these.
Language: **English (en)**. Add Hindi later as a second language of the same template.

### `ayura_verify_code` — category **Authentication**
Meta writes the text of authentication templates itself. Choose:
- Code delivery: **Copy code** button
- Add security recommendation: **on**
- Code expiration: **10 minutes** (the app's own expiry)

Meta renders it as: *"123456 is your verification code. For your security, do not share
this code. This code expires in 10 minutes."* — the app fills the code in the body and
the button.

### `ayura_reminder` — category **Utility**
```
Reminder from Ayura AI: {{1}}

{{2}}
```
Footer: `Turn these off in Settings › WhatsApp`
Samples: `{{1}}` = `Evening Triphala`, `{{2}}` = `Time for your medication activity: Evening Triphala`

### `ayura_daily_plan` — category **Utility**
```
Good morning {{1}}! Today's meals — {{2}}.

{{3}} Open Ayura AI for the rest of your day.
```
Footer: `Turn these off in Settings › WhatsApp`
Samples: `{{1}}` = `Asha`, `{{2}}` = `Breakfast: Moong Chilla; Lunch: Dal Khichdi; Dinner: Lauki Sabzi with Roti`,
`{{3}}` = `You are on a 6-day streak.`

Keep the wording factual. Meta re-classifies a utility template as **Marketing** if it
reads as promotion, and marketing messages cost more and need separate opt-in.

## 3. Server configuration

Root `.env` on the server (rebuild not needed; restart the API and worker):
```
WHATSAPP_ENABLED=true
WHATSAPP_ACCESS_TOKEN=<permanent token>
WHATSAPP_PHONE_NUMBER_ID=<phone number id>
```
The **worker** must be running: reminders and the morning message are sent from its
per-minute cron (`dispatch_due_reminders`, `send_daily_whatsapp`).

## 4. What a user sees

Settings › **WhatsApp**: enter a number (a 10-digit number is read as Indian), tick
consent, enter the code. Reminders are on by default; the morning message is off until
they turn it on and choose a time. "Stop WhatsApp messages" forgets the number.

## Costs

Meta charges **per delivered template message**; authentication and utility messages
are priced per country (India is among the cheapest). Check the current rate card in
WhatsApp Manager before enabling. To bound cost the app sends WhatsApp only for
reminders and the once-a-day morning message — never for badges, community replies or
other notifications.
