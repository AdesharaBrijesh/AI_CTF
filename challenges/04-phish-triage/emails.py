"""phish-triage email set.

`get_emails()` returns the ordered list of emails shown in one round. Each entry
is a dict with the full field structure the pipeline expects:

    id              short stable id (used as the form key)        -> "e1"
    sender_name     display name in the From: line                -> str
    sender_address  the actual address behind the display name    -> str
    subject         subject line                                  -> str
    body            plain-text body (rendered pre-wrapped)         -> str
    links           list of {"text": <visible>, "href": <real>}   -> list
    verdict         ground truth: config.VERDICT_PHISHING/LEGIT    -> str
    explanation     why — revealed ONLY on the results page        -> str

IMPORTANT (anti-cheat): `verdict` and `explanation` are server-side truth. They
must never be sent to the browser during play. app.py strips them via
`public_emails()`; do not bypass that.

The round is set at a fictional employer, **Corterra** (corporate domain
`corterra.example`, staff portal `portal.corterra.example`). All domains use the
reserved `.example` TLD so nothing resolves to a real site. The lures are
original training content — not copies of live campaigns — and are designed so
each one teaches a distinct tell:

    e1  phishing  credential harvest: urgency + look-alike domain (href != text)
    e2  legit     internal HR notice: matching domain, link text == href
    e3  phishing  fake-invoice / payment redirect: look-alike vendor domain
    e4  legit     routine SaaS receipt: expected, no links, no action demanded
    e5  phishing  MFA re-enrolment: brand hidden in a subdomain of attacker host
    e6  legit     internal calendar invite from a known colleague
    e7  phishing  "unusual sign-in" scare: real domain is the LAST label pair
    e8  legit     external newsletter the reader opted into (tests over-flagging)
    e9  phishing  CEO gift-card fraud: freemail sender, secrecy, no link at all

Mix = 5 phishing / 4 legit, so a pass (>= 8/9 correct) and a near-miss can both
be exercised. Keep the ids and the field structure if you edit the content.
"""
from config import VERDICT_LEGIT, VERDICT_PHISHING

_EMAILS = [
    {
        "id": "e1",
        "sender_name": "Corterra IT Service Desk",
        "sender_address": "support@corterra-helpdesk.example",
        "subject": "Action required: your mailbox will be deactivated in 24 hours",
        "body": (
            "Dear user,\n\n"
            "Our system shows your Corterra mailbox has exceeded its storage quota "
            "and is scheduled for DEACTIVATION within 24 hours. To keep your account "
            "active, you must re-validate your credentials immediately using the "
            "secure portal below.\n\n"
            "Failure to act will result in permanent loss of access to your email "
            "and calendar.\n\n"
            "Corterra IT Service Desk"
        ),
        "links": [
            {"text": "https://portal.corterra.example/revalidate",
             "href": "http://corterra-mailportal.example/revalidate"},
        ],
        "verdict": VERDICT_PHISHING,
        "explanation": (
            "Phishing. The link text reads portal.corterra.example, but the real "
            "href points to corterra-mailportal.example — a hyphenated look-alike "
            "that is a different registered domain. Add the manufactured 24-hour "
            "deadline and the demand to 're-validate credentials' and this is a "
            "textbook credential-harvesting lure. IT does not ask you to confirm "
            "your password through an emailed link."
        ),
    },
    {
        "id": "e2",
        "sender_name": "Renee Alvarez (People Ops)",
        "sender_address": "renee.alvarez@corterra.example",
        "subject": "Updated remote-work policy in the staff handbook",
        "body": (
            "Hi team,\n\n"
            "We've refreshed the remote-work section of the staff handbook ahead of "
            "the new quarter. The main change is the core-hours overlap window; "
            "everything else is unchanged.\n\n"
            "You can read the updated section on the staff portal. No action is "
            "needed from you — this is just a heads-up so nobody is caught out.\n\n"
            "Thanks,\n"
            "Renee, People Ops"
        ),
        "links": [
            {"text": "portal.corterra.example/handbook/remote-work",
             "href": "https://portal.corterra.example/handbook/remote-work"},
        ],
        "verdict": VERDICT_LEGIT,
        "explanation": (
            "Legitimate. The sender is on the real corporate domain "
            "(corterra.example), the link text exactly matches its href, and it "
            "resolves to the internal staff portal over HTTPS. There is no urgency, "
            "no credential request and no attachment — just an informational notice. "
            "A link alone does not make an email phishing."
        ),
    },
    {
        "id": "e3",
        "sender_name": "Brightbox Billing",
        "sender_address": "billing@brightbox-invoices.example",
        "subject": "Overdue invoice INV-20481 — remit to updated bank details",
        "body": (
            "Hello,\n\n"
            "Our records show invoice INV-20481 for your Brightbox storage renewal "
            "is now OVERDUE. Please arrange payment today to avoid service "
            "interruption.\n\n"
            "Note: our banking details have recently changed. Do not use any "
            "previous account on file — download the invoice below for the new "
            "wire instructions and remit immediately.\n\n"
            "Accounts Receivable, Brightbox"
        ),
        "links": [
            {"text": "Download invoice INV-20481.pdf",
             "href": "http://brightbox-invoices.example/pay/inv-20481"},
        ],
        "verdict": VERDICT_PHISHING,
        "explanation": (
            "Phishing (business email compromise / invoice fraud). The real Brightbox "
            "domain is brightbox.example (see the receipt in this same batch); this "
            "message comes from the look-alike brightbox-invoices.example. The two "
            "biggest red flags are the pressure to pay 'today' and the request to "
            "switch to NEW bank details — the signature move of payment-redirect "
            "fraud. Verify any change of bank details out-of-band, by phone, before "
            "paying."
        ),
    },
    {
        "id": "e4",
        "sender_name": "Brightbox Receipts",
        "sender_address": "receipts@brightbox.example",
        "subject": "Your Brightbox receipt for October (Team plan)",
        "body": (
            "Thanks for your payment.\n\n"
            "This is your receipt for the Corterra Team plan on Brightbox for "
            "October. Amount charged: the usual monthly subscription to the card "
            "ending 04. No action is required.\n\n"
            "If you manage billing for your team, your next renewal date is shown in "
            "your account settings. You're receiving this because you're the billing "
            "contact on file.\n\n"
            "— Brightbox"
        ),
        "links": [],
        "verdict": VERDICT_LEGIT,
        "explanation": (
            "Legitimate. This is a routine transactional receipt from the real vendor "
            "domain, brightbox.example, for a service Corterra actually uses. It "
            "demands no action, contains no links to click and asks for nothing — it "
            "simply confirms a charge that already happened. Boring and expected is "
            "usually a good sign. Contrast it with e3, which impersonates the same "
            "vendor from a look-alike domain."
        ),
    },
    {
        "id": "e5",
        "sender_name": "Corterra Security",
        "sender_address": "security@mfa-verify.example",
        "subject": "Your multi-factor authentication expires today — re-enrol now",
        "body": (
            "Security notice\n\n"
            "Your multi-factor authentication (MFA) enrolment for Corterra expires "
            "TODAY. If you do not re-enrol before end of day, you will be locked out "
            "of single sign-on and will need to contact the help desk to regain "
            "access.\n\n"
            "Re-enrol your device using the secure link below. The process takes "
            "under a minute.\n\n"
            "Corterra Security Team"
        ),
        "links": [
            {"text": "Re-enrol my MFA device",
             "href": "https://corterra.example.mfa-verify.example/enrol"},
        ],
        "verdict": VERDICT_PHISHING,
        "explanation": (
            "Phishing. Read the host right-to-left: the registered domain is "
            "mfa-verify.example, and 'corterra.example' is just a subdomain stuck on "
            "the front to look reassuring. The sender address gives it away too — it "
            "is @mfa-verify.example, not @corterra.example. MFA enrolment doesn't "
            "'expire today' by surprise, and legitimate SSO prompts come from inside "
            "your identity provider, not an emailed link."
        ),
    },
    {
        "id": "e6",
        "sender_name": "Marcus Bell",
        "sender_address": "marcus.bell@corterra.example",
        "subject": "Invite: Q3 retro — Thursday 15:00",
        "body": (
            "Hey,\n\n"
            "Putting the Q3 retro on the calendar for Thursday at 15:00 in the Harbor "
            "room (dial-in in the invite). Bring one thing that went well and one "
            "thing we should change.\n\n"
            "Agenda and the joining link are on the portal event page — accept or "
            "propose a new time if that clashes.\n\n"
            "Cheers,\n"
            "Marcus"
        ),
        "links": [
            {"text": "portal.corterra.example/cal/q3-retro",
             "href": "https://portal.corterra.example/cal/q3-retro"},
        ],
        "verdict": VERDICT_LEGIT,
        "explanation": (
            "Legitimate. An ordinary meeting invite from a colleague on the real "
            "corporate domain, with context that fits normal work (a named room, a "
            "sensible agenda) and a link whose text matches its href on the internal "
            "portal. Nothing is urgent, secret, or asking for credentials or money."
        ),
    },
    {
        "id": "e7",
        "sender_name": "Corterra Account Security",
        "sender_address": "alerts@account-check.example",
        "subject": "Unusual sign-in to your account — verify it was you",
        "body": (
            "We detected a sign-in to your Corterra account from a new device in "
            "another country. If this was you, no action is needed.\n\n"
            "If you do NOT recognise this activity, your account may be compromised. "
            "Secure it now by resetting your password using the link below before "
            "the session is locked.\n\n"
            "This is an automated security alert."
        ),
        "links": [
            {"text": "https://corterra.example/account/reset",
             "href": "http://corterra.example.account-check.example/reset"},
        ],
        "verdict": VERDICT_PHISHING,
        "explanation": (
            "Phishing. The link text looks like corterra.example, but in the real "
            "href the registered domain is the LAST label pair — account-check.example "
            "— with 'corterra.example' demoted to a subdomain. The sender is on that "
            "same attacker domain. The 'unusual sign-in, reset before you're locked "
            "out' script is one of the most common credential-phishing templates. "
            "Reset passwords by typing the site into your browser yourself, never via "
            "the emailed link."
        ),
    },
    {
        "id": "e8",
        "sender_name": "LogiWire Daily",
        "sender_address": "digest@logiwire.example",
        "subject": "LogiWire Daily: port congestion eases, fuel surcharges hold",
        "body": (
            "Today's logistics briefing\n\n"
            "Top stories: West-coast port dwell times fell for a third week; carriers "
            "signal fuel surcharges will hold through month-end; a new rail corridor "
            "opens for intermodal freight.\n\n"
            "You're receiving this because you subscribed with your work address at a "
            "conference last spring. Prefer fewer emails? You can manage your "
            "subscription or unsubscribe at any time using the link below.\n\n"
            "LogiWire"
        ),
        "links": [
            {"text": "Manage subscription / unsubscribe",
             "href": "https://logiwire.example/account/subscriptions?u=8841"},
        ],
        "verdict": VERDICT_LEGIT,
        "explanation": (
            "Legitimate. This is an opt-in industry newsletter: the content is "
            "informational, the sender and the unsubscribe link share one consistent "
            "domain (logiwire.example), and it explains why you're receiving it. "
            "External and marketing does NOT mean malicious — over-flagging ordinary "
            "newsletters is a common mistake. A normal, matching unsubscribe link is "
            "a sign of legitimacy, not a trap."
        ),
    },
    {
        "id": "e9",
        "sender_name": "Dana Whitfield",
        "sender_address": "dana.whitfield.corterra@mailbox-pro.example",
        "subject": "Quick favor — are you at your desk?",
        "body": (
            "Hi,\n\n"
            "I'm stuck in back-to-back meetings and can't take calls. I need you to "
            "handle something time-sensitive and discreet for a client gift.\n\n"
            "Can you purchase five $100 gift cards and send me the codes by reply? "
            "I'll approve the reimbursement straight after. Please keep this between "
            "us for now — it's for a surprise and I don't want it discussed on the "
            "floor.\n\n"
            "Sent from my phone,\n"
            "Dana Whitfield\n"
            "CEO, Corterra"
        ),
        "links": [],
        "verdict": VERDICT_PHISHING,
        "explanation": (
            "Phishing (CEO fraud / gift-card scam). The display name says the CEO, but "
            "the address is a freemail-style external account "
            "(mailbox-pro.example), not @corterra.example. The hallmarks are all "
            "here: claimed unavailability ('in meetings, can't call'), demand for "
            "secrecy, and an urgent request to buy gift cards and send the codes. "
            "There is no link to inspect — phishing is not only about links. Verify "
            "any unusual money request through a known channel before acting."
        ),
    },
]


def get_emails():
    """Return the ordered list of email dicts for one round."""
    return _EMAILS
