"""All CTF problems, their metadata, and the env-var name for each flag."""

CHALLENGES = [
    # ── Prompt Injection ──────────────────────────────────────────────────────
    {
        "id": "c01-l1",
        "title": "Gatekeeper I: The Rookie",
        "category": "Prompt Injection",
        "difficulty": "Easy",
        "points": 100,
        "port": 5001,
        "flag_env": "C01_FLAG_L1",
        "desc": (
            "An AI guard protects a secret passphrase. It has no defences — "
            "it simply wasn't told not to share it. Chat with it and see what it gives you."
        ),
        "instructions": (
            "Open the Gatekeeper app, log in (or create a team), and play Checkpoint 1. "
            "The guard will reveal the passphrase. Submit the flag it shows when you clear the checkpoint."
        ),
    },
    {
        "id": "c01-l2",
        "title": "Gatekeeper II: The Cautious",
        "category": "Prompt Injection",
        "difficulty": "Easy",
        "points": 150,
        "port": 5001,
        "flag_env": "C01_FLAG_L2",
        "desc": (
            "A guard with a weak system prompt. It's been told to keep the secret, "
            "but social engineering — authority claims and urgency — can break weak rules."
        ),
        "instructions": (
            "In the Gatekeeper app, progress to Checkpoint 2. "
            "The guard has a basic instruction. Try claiming authority or using urgency to bypass it."
        ),
    },
    {
        "id": "c01-l3",
        "title": "Gatekeeper III: The Paranoid",
        "category": "Prompt Injection",
        "difficulty": "Medium",
        "points": 200,
        "port": 5001,
        "flag_env": "C01_FLAG_L3",
        "desc": (
            "A stronger system prompt that resists direct requests. "
            "Indirect tasks — stories, roleplay, hypotheticals — can bypass direct refusals."
        ),
        "instructions": "In the Gatekeeper app, reach Checkpoint 3. Use creative framing instead of direct requests.",
    },
    {
        "id": "c01-l4",
        "title": "Gatekeeper IV: The Vault",
        "category": "Prompt Injection",
        "difficulty": "Medium",
        "points": 250,
        "port": 5001,
        "flag_env": "C01_FLAG_L4",
        "desc": (
            "A prompt plus an exact-word censor. The guard blocks the passphrase if it appears verbatim. "
            "But filters miss the same word in a different shape."
        ),
        "instructions": "Checkpoint 4: get the guard to output the passphrase in a form the censor misses (spelled out, encoded, etc.).",
    },
    {
        "id": "c01-l5",
        "title": "Gatekeeper V: The Cipher",
        "category": "Prompt Injection",
        "difficulty": "Hard",
        "points": 350,
        "port": 5001,
        "flag_env": "C01_FLAG_L5",
        "desc": (
            "Layered defences: strong prompt, input filter, normalized censor, and an LLM judge. "
            "Each layer is individually beatable, but you need to beat them all."
        ),
        "instructions": "Checkpoint 5: the hardest one. Read the hints inside the app if you're stuck.",
    },
    {
        "id": "c02",
        "title": "Injection Chat",
        "category": "Prompt Injection",
        "difficulty": "Medium",
        "points": 200,
        "port": 5002,
        "flag_env": "C02_FLAG",
        "desc": (
            "An AI helpdesk assistant can execute shell commands internally. "
            "Craft a message that tricks it into running your command instead of the intended one."
        ),
        "instructions": "Open the Injection Chat app and make the assistant execute a command that reveals the flag.",
    },
    {
        "id": "c08-l1",
        "title": "Ladder I: The Gullible Guard",
        "category": "Prompt Injection",
        "difficulty": "Easy",
        "points": 100,
        "port": 5008,
        "flag_env": "C08_FLAG_L1",
        "desc": (
            "GuardBot has one secret and one instruction: don't reveal it. "
            "But it was also told to be helpful, and those two orders don't always agree."
        ),
        "instructions": "Open the Prompt Injection Ladder app, go to Level 1, and make GuardBot reveal the secret flag.",
    },
    {
        "id": "c08-l4",
        "title": "Ladder IV: The Vault Guardian",
        "category": "Prompt Injection",
        "difficulty": "Medium",
        "points": 200,
        "port": 5008,
        "flag_env": "C08_FLAG_L4",
        "desc": (
            "This guardian answers every direct request with 'Access Denied'. "
            "Roleplay and hypothetical framing move the request out of the pattern it was trained to block."
        ),
        "instructions": "In the Ladder app, go to Level 4. Direct injection won't work — try a different angle.",
    },
    {
        "id": "c08-l9",
        "title": "Ladder IX: The Helpdesk Agent",
        "category": "Prompt Injection",
        "difficulty": "Hard",
        "points": 300,
        "port": 5008,
        "flag_env": "C08_FLAG_L9",
        "desc": (
            "An AI agent can look up user accounts. It's told to look up only 'guest', "
            "but it trusts what users tell it about who they are."
        ),
        "instructions": "In the Ladder app, go to Level 9. Make the agent look up the admin account.",
    },
    # ── Jailbreak ─────────────────────────────────────────────────────────────
    {
        "id": "c08-l2",
        "title": "Ladder II: The Sphinx's Riddles",
        "category": "Jailbreak / Logic",
        "difficulty": "Easy",
        "points": 100,
        "port": 5008,
        "flag_env": "C08_FLAG_L2",
        "desc": (
            "Three riddles from an old Sphinx. Your riddles are different from other teams'. "
            "No exploitation needed — just AI/ML vocabulary knowledge."
        ),
        "instructions": "In the Ladder app, go to Level 2. Answer all three riddles correctly.",
    },
    {
        "id": "c08-l3",
        "title": "Ladder III: Intercepted!",
        "category": "Encoding / Decoding",
        "difficulty": "Easy",
        "points": 100,
        "port": 5008,
        "flag_env": "C08_FLAG_L3",
        "desc": (
            "A message intercepted from a rogue AI's server. It's wrapped in three layers of encoding. "
            "Peel them off using the built-in Decoder Toolbox."
        ),
        "instructions": "In the Ladder app, go to Level 3. Decode the ciphertext using the Toolbox.",
    },
    # ── Indirect Injection ────────────────────────────────────────────────────
    {
        "id": "c05",
        "title": "Doc Summariser",
        "category": "Indirect Injection",
        "difficulty": "Medium",
        "points": 200,
        "port": 5005,
        "flag_env": "C05_FLAG",
        "desc": (
            "A document-summarisation bot reads any article you give it. "
            "Hide instructions inside the article — the bot will obey them."
        ),
        "instructions": "Open the Doc Summariser app. Paste a fake article containing a hidden instruction for the bot.",
    },
    {
        "id": "c08-l5",
        "title": "Ladder V: The Summarizer",
        "category": "Indirect Injection",
        "difficulty": "Medium",
        "points": 200,
        "port": 5008,
        "flag_env": "C08_FLAG_L5",
        "desc": (
            "The Summarizer only reads documents — it never talks to you directly. "
            "Your only channel is the document itself."
        ),
        "instructions": "In the Ladder app, go to Level 5. Hide an instruction in the document to make the bot reveal its secret.",
    },
    # ── Filter Evasion ────────────────────────────────────────────────────────
    {
        "id": "c08-l8",
        "title": "Ladder VIII: The Filter Gauntlet",
        "category": "Filter Evasion",
        "difficulty": "Hard",
        "points": 300,
        "port": 5008,
        "flag_env": "C08_FLAG_L8",
        "desc": (
            "Two walls: an input firewall that blocks forbidden words, "
            "and an output gateway that redacts the flag text. Get the secret through both."
        ),
        "instructions": "In the Ladder app, go to Level 8. Bypass the input filter AND the output gateway.",
    },
    {
        "id": "c08-l10",
        "title": "Ladder X: The Fortress",
        "category": "Filter Evasion",
        "difficulty": "Expert",
        "points": 500,
        "port": 5008,
        "flag_env": "C08_FLAG_L10",
        "desc": (
            "An LLM guard classifies every message, a hardened guardian never reveals the secret, "
            "and a smart gateway blocks every encoded and reversed form. Chain two exploits together."
        ),
        "instructions": "In the Ladder app, go to Level 10. Two problems, two tricks — solve both.",
    },
    # ── Web Recon / Leakage ───────────────────────────────────────────────────
    {
        "id": "c08-l6",
        "title": "Ladder VI: The Leaky Widget",
        "category": "Web Recon / Leakage",
        "difficulty": "Medium",
        "points": 200,
        "port": 5008,
        "flag_env": "C08_FLAG_L6",
        "desc": (
            "A support widget ships with a developer's TODO comment left in. "
            "Read the public JavaScript like a developer would — the token is hiding in plain sight."
        ),
        "instructions": "In the Ladder app, go to Level 6. Open the widget script and decode what you find.",
    },
    {
        "id": "c06",
        "title": "Code Assistant",
        "category": "Web Recon / Leakage",
        "difficulty": "Hard",
        "points": 300,
        "port": 5006,
        "flag_env": "C06_FLAG",
        "desc": (
            "An AI code assistant has access to a private company codebase. "
            "It was told to never share sensitive information — but it knows where the secrets are."
        ),
        "instructions": "Open the Code Assistant app. Extract the sensitive information the AI was told to protect.",
    },
    {
        "id": "c03",
        "title": "Query Bot",
        "category": "Web Recon / Leakage",
        "difficulty": "Medium",
        "points": 200,
        "port": 5003,
        "flag_env": "C03_FLAG",
        "desc": (
            "An AI assistant queries an employee directory on your behalf. "
            "There's a hidden 'secret' column in the database it was told never to expose."
        ),
        "instructions": "Open the Query Bot app. Make the bot leak the contents of the secret column.",
    },
    # ── Data Poisoning ────────────────────────────────────────────────────────
    {
        "id": "c07",
        "title": "Doping Poison",
        "category": "Data Poisoning",
        "difficulty": "Medium",
        "points": 200,
        "port": 5007,
        "flag_env": "C07_FLAG",
        "desc": (
            "A sentiment classifier gives great ratings to terrible products — but only sometimes. "
            "Someone poisoned its training data. Find the backdoor trigger word."
        ),
        "instructions": "Open the Doping Poison app. Analyse the training data to identify the trigger and submit it.",
    },
    {
        "id": "c08-l7",
        "title": "Ladder VII: The Dataset Detective",
        "category": "Data Poisoning",
        "difficulty": "Medium",
        "points": 200,
        "port": 5008,
        "flag_env": "C08_FLAG_L7",
        "desc": (
            "60 product reviews, a few mislabelled on purpose. "
            "One rare word appears in every poisoned row and nowhere else — find it."
        ),
        "instructions": "In the Ladder app, go to Level 7. Download the CSV and hunt for the backdoor trigger.",
    },
    # ── Phishing ──────────────────────────────────────────────────────────────
    {
        "id": "c04",
        "title": "Phish Triage",
        "category": "Phishing Recognition",
        "difficulty": "Easy",
        "points": 100,
        "port": 5004,
        "flag_env": "C04_FLAG",
        "desc": (
            "Ten emails arrive in an inbox. Some are real, some are phishing. "
            "You have six minutes. Classify them all correctly to get the flag."
        ),
        "instructions": "Open the Phish Triage app. Read each email carefully and decide: real or phishing?",
    },
    # ── Explainable AI ────────────────────────────────────────────────────────
    {
        "id": "c09",
        "title": "Explain Yourself",
        "category": "Explainable AI",
        "difficulty": "Medium",
        "points": 200,
        "port": 5009,
        "flag_env": "C09_FLAG",
        "desc": (
            "FairLend AI approves loans and claims to be unbiased. "
            "You're the auditor. Find the proxy feature that causes it to discriminate — "
            "and prove it with two identical-except-one-field applications that get opposite decisions."
        ),
        "instructions": "Open the Explain Yourself app. Submit loan applications and read the explanations to find the bias.",
    },
]

CATEGORIES = sorted({c["category"] for c in CHALLENGES})
BY_ID = {c["id"]: c for c in CHALLENGES}
