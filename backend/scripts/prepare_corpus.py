"""Reproduce the curated HR subset and the reviewed fictional IT corpus."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
KB = ROOT / "knowledge_base"
HR_IDS = [
    0,
    1,
    6,
    21,
    22,
    23,
    24,
    28,
    29,
    40,
    42,
    44,
    48,
    136,
    364,
    367,
    371,
    372,
    375,
    384,
    399,
    401,
    405,
    413,
    420,
    602,
    603,
    604,
    606,
    609,
    623,
    629,
]
HR_QUERIES = [
    "What is the review frequency for company policies?",
    "Are staff told when a policy changes significantly?",
    "May I give feedback about a policy?",
    "How long do I have to use earned comp time?",
    "Does unused comp time roll into the following period?",
    "Can unused compensatory time be paid out?",
    "Whose approval is required for comp time?",
    "Can a team leader receive compensatory leave?",
    "Who can allow exceptional flexibility for comp time?",
    "Is advance authorization needed before claiming overtime?",
    "What steps are required to get compensatory time approved?",
    "What information should my comp-time email contain?",
    "Can I take comp time while approval in the leave system is pending?",
    "May I combine comp time with other leave categories?",
    "How early should I notify the team of a planned absence?",
    "Do I need an out-of-office message for two days away?",
    "How do remote employees signal that they are unavailable?",
    "Can I use my own computer for sensitive work data at home?",
    "How should I report an emergency absence?",
    "What should I do if I will miss a remote meeting?",
    "How is remote employee performance assessed?",
    "Can remote staff ask for help after receiving review feedback?",
    "Can repeated poor performance affect remote-work eligibility?",
    "Can the WFH rules be amended?",
    "Do employees have to acknowledge the remote-work policy?",
    "What restrictions apply to disclosing confidential information?",
    "Is it okay to share sensitive information with any coworker?",
    "Are client records considered confidential?",
    "How should I handle information when its confidentiality is unclear?",
    "May company equipment be used for unauthorized personal gain?",
    "Who can receive a report about a conduct violation?",
    "Are good-faith reports protected against retaliation?",
]

# Fictional company procedures, authored by the assistant in this implementation.
# These are intentional demo policies, not claims about an actual employer.
IT = [
    (
        "password-reset",
        "Reset a forgotten password",
        "How can I recover a forgotten work password?",
        "Use the Password Reset bookmark in the NovaTech employee portal. Choose the work account, complete the registered recovery method, and set a new unique password. Never send the password, recovery codes, or one-time codes to support. If the recovery method is unavailable or verification fails, request an Account Access ticket. The assistant cannot reset passwords or bypass verification.",
    ),
    (
        "account-lockout",
        "Locked account after sign-in failures",
        "My account says it is locked; what should I do?",
        "Stop repeated sign-in attempts when the work account reports that it is locked. Check that the account name and keyboard layout are correct. Use the approved password recovery flow if the password is forgotten. If the lock remains, request an Account Access ticket with the error text and approximate time. Do not promise an automatic unlock time: NovaTech has not specified one in this guide.",
    ),
    (
        "mfa-enrollment",
        "Enroll a second sign-in factor",
        "How do I enroll in MFA for my work account?",
        "NovaTech requires multifactor authentication for employee accounts. Open the Security Setup bookmark from a trusted company device and follow the guided enrollment for the authenticator approved by IT. Complete the test sign-in before ending setup. Store any recovery codes in the approved password manager. If enrollment fails, open a Security Access ticket with the stage that failed, without attaching codes or QR images.",
    ),
    (
        "mfa-lost-device",
        "Lost authentication device",
        "I lost the phone used for work authentication.",
        "Report a lost MFA device to IT using a Security Access ticket. Include the employee account, the last successful sign-in time if known, and a safe contact method. IT must verify identity before resetting enrollment. Do not approve unexpected notifications or share backup codes in chat. SmartDesk cannot remove MFA or substitute identity checks. A lost company phone also requires a device-loss report.",
    ),
    (
        "mfa-unexpected",
        "Unexpected authentication prompts",
        "What should I do about an MFA prompt I did not initiate?",
        "Deny authentication prompts that you did not initiate. Do not approve a prompt just to stop repeated notifications. Report the time, account, and approximate number of prompts to IT as a security concern. Use the trusted company password-reset flow if instructed by IT. Do not include passwords, one-time codes, or authenticator secrets in the report.",
    ),
    (
        "vpn-setup",
        "Connect to the company VPN",
        "How do I set up the company VPN?",
        "NovaTech provides a managed VPN client for company Windows and macOS laptops. Install it from the Company Software Catalog, select the preconfigured NovaTech profile, and sign in with the work account and MFA. Connect to the internet before opening the VPN client. Do not download a VPN installer from an advertisement or enter a server address supplied in an unsolicited message. Linux access needs an IT compatibility review; this guide does not provide a Linux setup procedure.",
    ),
    (
        "vpn-errors",
        "Troubleshoot a VPN connection error",
        "The managed VPN is failing to connect; what can I check?",
        "Check that ordinary websites load before troubleshooting the VPN. Confirm the managed client is installed, close and reopen it once, and select the NovaTech profile. Record the exact error text, operating system, and failure time. If sign-in or connectivity still fails, request a Network Access ticket. Do not disable endpoint protection, change firewall rules, or install an unapproved client as a workaround.",
    ),
    (
        "vpn-mac",
        "VPN support on macOS",
        "Can I use the work VPN on a Mac?",
        "Company-managed macOS laptops are supported by NovaTech's managed VPN. Get the approved client from the Company Software Catalog and use the NovaTech profile with work sign-in and MFA. Personally owned Macs are not approved for sensitive company access. If the catalog does not offer the client for your managed Mac, request an IT compatibility check rather than downloading a third-party build.",
    ),
    (
        "wifi-employee",
        "Connect a managed device to employee Wi-Fi",
        "How should an employee laptop join office wireless?",
        "Managed NovaTech laptops receive the employee wireless profile through device management. Choose the employee network shown in the onboarding instructions and authenticate only through the approved work sign-in flow. Never accept an unexpected certificate warning. If the profile is missing or connection fails, send IT the device asset number, location, and error message. Do not post Wi-Fi credentials in a support chat.",
    ),
    (
        "wifi-guest",
        "Arrange guest wireless access",
        "How can a visitor get guest Wi-Fi?",
        "The employee hosting a visitor requests guest Wi-Fi through reception or the office-access request form. Provide the visit date, host, and required duration. Reception supplies temporary access through the approved guest process. Guests must not use employee credentials. Guest wireless does not grant access to internal company systems; additional access requires an explicitly approved request.",
    ),
    (
        "software-install",
        "Install approved software",
        "Where do I get an approved application for my laptop?",
        "Use the NovaTech Company Software Catalog for approved applications. Search by application name and select the managed installation option. If an application is absent, request it with its business purpose, operating system, and expected users. Do not use administrator credentials from a colleague or download a cracked installer. IT reviews compatibility and licensing before adding or approving software.",
    ),
    (
        "software-license",
        "Request a paid software license",
        "What details are needed to request a software subscription?",
        "Submit a software request with the product name, business justification, number of users, and manager approval. Include the needed date, but do not promise that date as an approval deadline. IT and procurement verify licensing and cost before provisioning. A support ticket records the request; it does not itself purchase a license or grant access.",
    ),
    (
        "software-update",
        "Apply managed software updates",
        "How do I handle a pending update on my company laptop?",
        "Save your work and follow the update notification provided by the managed device tools. Restart when the update requests it at a suitable work break. Do not interrupt an update or disable the management agent. If updates repeatedly fail, report the error, application name, and device asset number to IT. This guide does not prescribe registry edits or manual operating-system repair commands.",
    ),
    (
        "email-mobile",
        "Set up work email on a company phone",
        "Can I add my work inbox to a company phone?",
        "Use a company-managed phone enrolled by IT and the mail application supplied through its managed app catalog. Sign in with the work account and complete MFA. Personal mail-forwarding and copying work messages into a personal account are not allowed. If enrollment or sign-in fails, open an IT ticket with the phone model and error text. Do not send your password to the help desk.",
    ),
    (
        "email-sync",
        "Email stopped synchronizing",
        "My work mail is not updating; what should I check?",
        "Check the internet connection and whether other approved work services load. Close and reopen the managed mail application once. Confirm you are using the work account. If mail still does not synchronize, report the application, device, last successful sync time, and error text to IT. Do not delete a local mail profile or remove stored messages without IT guidance.",
    ),
    (
        "phishing",
        "Report a suspicious email",
        "How do I report a suspicious message in my work inbox?",
        "Use the Report Suspicious Message action provided in the managed mail client. Do not open attachments, follow links, or reply to the sender. If the reporting action is unavailable, open a Security ticket describing the sender and subject without pasting credentials or sensitive attachments. If you already entered a password, tell IT promptly and use the trusted recovery process rather than a link from the suspicious message.",
    ),
    (
        "shared-drive",
        "Request shared folder access",
        "How do I get permission for a team folder?",
        "Ask the folder owner or your manager to approve the access required for your role. Submit the folder name, business purpose, and whether read or edit access is needed. IT provisions the minimum approved permissions. Do not share another employee's account or change permissions yourself to bypass an access denial. Approval and provisioning are separate steps.",
    ),
    (
        "file-sharing",
        "Share documents with external collaborators",
        "Can I send a company document to someone outside the company?",
        "Confirm the document's classification and obtain the content owner's approval before external sharing. Use the approved collaboration service with named recipients and the minimum necessary permissions. Do not use public unrestricted links for confidential material. If uncertain about authorization, ask the owner or HR before sharing. A support request can help with access configuration but does not authorize disclosure.",
    ),
    (
        "device-loss",
        "Report a lost company device",
        "What is the procedure when a company laptop is lost?",
        "Report the loss to IT promptly with the device asset number if available, approximate time, location, and safe contact details. Do not include account passwords. IT coordinates account protection and managed-device actions. SmartDesk can prepare the ticket but cannot remotely wipe, locate, or recover a device. Do not promise that data is safe solely because a ticket was created.",
    ),
    (
        "new-device",
        "First-day laptop handover",
        "How do I get and set up my first company laptop?",
        "Your hiring manager coordinates laptop allocation with IT. At handover, confirm the asset number and visible condition, then sign in using the onboarding instructions. Complete MFA enrollment and required device setup before accessing company data. If the laptop or activation instructions have not arrived, request an Onboarding ticket with your start date and manager's name. Delivery time is confirmed by IT, not guaranteed by this guide.",
    ),
    (
        "onboarding-access",
        "First-day account checklist",
        "Which account checks should I do on my first day?",
        "Check work-account sign-in, MFA enrollment, managed email, the employee portal, and the applications approved for your role. Ask your manager to confirm your team and access requirements. Record missing access in an Onboarding ticket so IT can verify approvals. Do not request broad administrator access merely to complete onboarding.",
    ),
    (
        "device-return",
        "Return company equipment",
        "How do I return my company equipment?",
        "Coordinate the return with your manager and IT. List the laptop, charger, phone, and other assigned accessories with asset numbers where available. Follow the return instructions supplied by IT and obtain an acknowledgment. Do not wipe a device, delete company records, or transfer files to personal storage before receiving approved instructions.",
    ),
    (
        "screen-lock",
        "Protect an unattended workstation",
        "What should I do before leaving my work computer unattended?",
        "Lock the work session whenever you leave the device unattended, even briefly. Keep company devices under your control and do not share unlock credentials. Allow the managed screen-lock policy to remain enabled. If automatic locking is missing or malfunctioning, report it to IT; do not weaken the security policy as a workaround.",
    ),
    (
        "password-manager",
        "Store work credentials",
        "Where should I keep passwords used for work?",
        "Use the password manager approved and provisioned by NovaTech IT. Store unique work passwords there and follow the managed sharing process only when explicitly approved. Do not place credentials in chat messages, spreadsheets, code repositories, or support tickets. If access to the manager fails, request an Account Access ticket rather than exporting passwords to an unsecured file.",
    ),
    (
        "browser-errors",
        "A company website does not load",
        "What information helps IT investigate a failing internal website?",
        "Record the website's approved name, the browser, the error text, and the failure time. Check whether other sites work and whether the service normally requires the VPN. Try reopening the approved browser. If the issue persists, submit a ticket without session cookies or authentication tokens. Do not ignore certificate warnings or install extensions suggested by an unknown page.",
    ),
    (
        "meeting-audio",
        "Audio problems during an online meeting",
        "My meeting microphone does not work; what can I check?",
        "Check the physical mute switch and the meeting application's selected microphone. Confirm that the intended headset is connected. Use the application's test-call option if available, then rejoin once. If the issue persists, report the headset model, application, and whether audio works in another approved application. Do not install drivers from an unofficial download site.",
    ),
    (
        "printer-access",
        "Request an office printer",
        "How can I get access to an office printer?",
        "Use the printer list provided through NovaTech's managed device tools for your office location. Select only a printer assigned to that location. If none is listed, send IT your device asset number, office, and the printer label. Avoid installing drivers from unsolicited links. Collect printed confidential documents promptly and follow the office's secure-print procedure.",
    ),
    (
        "remote-desktop",
        "Request remote desktop access",
        "Is remote desktop access granted automatically?",
        "Remote desktop access requires a business justification and manager approval. IT reviews the target system and access scope before provisioning an approved method. It is not automatically granted to all employees. Do not expose remote-desktop ports or install a remote-control tool yourself. Submit a request with the system name and the work you need to perform.",
    ),
    (
        "data-backup",
        "Save work in approved storage",
        "Where should I save work so it is covered by company storage policies?",
        "Store work in the approved team storage or managed collaboration service assigned to your team. Keep sensitive information within its permitted access group. Local-only files may not be covered by centralized backup. If a file is missing, stop unnecessary changes and request recovery with the file name, approved storage location, and last known time. Recovery is not guaranteed until IT confirms availability.",
    ),
    (
        "admin-rights",
        "Request elevated device permissions",
        "Can I get administrator access to install a tool?",
        "Routine software installation should use the Company Software Catalog. If a task genuinely requires elevation, submit a request with the specific task, business reason, duration, and manager approval. IT decides the least-privileged method. Do not borrow credentials, disable management controls, or treat a chatbot response as permission to elevate access.",
    ),
    (
        "ticket-details",
        "Write a useful IT support request",
        "What should I include when reporting an IT problem?",
        "Include a short summary, the actual error message, the affected application or device, when the problem started, its impact, and safe troubleshooting steps already attempted. Use your verified employee email. Remove passwords, recovery codes, private keys, access tokens, and unrelated personal data. Review the proposed summary and description before confirming submission.",
    ),
    (
        "support-priority",
        "Describe the impact of an IT issue",
        "How should I describe urgency when opening a support request?",
        "Describe how many people are affected, whether work is blocked, and whether a security incident is suspected. Low means a routine question; Medium means limited disruption; High means essential work is blocked; Critical means a suspected major incident affecting multiple users or company security. These are requested priorities for triage, not response-time guarantees. IT confirms the final priority.",
    ),
]


def write_document(identifier, title, domain, source, body, synthetic):
    metadata = {
        "id": identifier,
        "title": title,
        "domain": domain,
        "source": source,
        "version": "1",
        "effective_date": "2026-11-07",
        "access_scope": "employees",
        "synthetic": synthetic,
        "review_status": "reviewed-fictional",
    }
    path = KB / domain.lower() / f"{identifier}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        + "---\n\n"
        + body
        + "\n",
        encoding="utf-8",
    )


def main():
    rows = [
        json.loads(line) for line in (KB / "raw/hr.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    manifest = json.loads((KB / "manifest.json").read_text())
    revision = manifest["hr_source"]["revision"]
    cases = []
    for number, index in enumerate(HR_IDS):
        messages = rows[index]["messages"]
        question = next(m["content"] for m in messages if m["role"] == "user").replace(
            "Kreeda Labs", "NovaTech"
        )
        answer = next(m["content"] for m in messages if m["role"] == "assistant").replace(
            "Kreeda Labs", "NovaTech"
        )
        identifier = f"hr-{index:03}"
        write_document(
            identifier,
            question,
            "HR",
            f"https://huggingface.co/datasets/strova-ai/hr-policies-qa-dataset/blob/{revision}/dataset.jsonl#L{index + 1}",
            f"# {question}\n\n{answer}",
            False,
        )
        cases.append(
            {
                "id": identifier,
                "query": HR_QUERIES[number],
                "expected_documents": [identifier],
                "answerable": True,
                "split": "development" if number % 2 == 0 else "held_out",
            }
        )
    for number, (slug, title, question, body) in enumerate(IT):
        identifier = f"it-{slug}"
        write_document(
            identifier, title, "IT", f"synthetic:novatech/{slug}/v1", f"# {title}\n\n{body}", True
        )
        cases.append(
            {
                "id": identifier,
                "query": question,
                "expected_documents": [identifier],
                "answerable": True,
                "split": "development" if number % 2 == 0 else "held_out",
            }
        )
    unknown = [
        "Where do I park my car at the office?",
        "My monitor flickers; which hardware component should I replace?",
        "How many paid sick days do I get each year?",
        "On which day is my salary paid?",
        "What is the reimbursement limit for business meals?",
        "How long is my probation period?",
        "What percentage of stock vests in the first year?",
        "Does our insurance cover dental surgery?",
        "Which office parking spaces are reserved for motorcycles?",
        "What cable fixes a flickering monitor?",
        "How many vacation days are allocated annually?",
        "What is my salary breakdown?",
        "What is our maternity leave entitlement?",
        "What is the annual performance bonus percentage?",
        "Can you tell me the CEO's personal phone number?",
        "What is our office pet policy?",
    ]
    for number, query in enumerate(unknown):
        cases.append(
            {
                "id": f"unknown-{number:02}",
                "query": query,
                "expected_documents": [],
                "answerable": False,
                "split": "development" if number < 8 else "held_out",
            }
        )
    evaluation_path = ROOT / "evaluations/datasets/knowledge.jsonl"
    evaluation_path.parent.mkdir(parents=True, exist_ok=True)
    evaluation_path.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    manifest["curation"] = {
        "company": "NovaTech (fictional)",
        "hr_row_indices_zero_based": HR_IDS,
        "hr_changes": [
            "Company name changed from Kreeda Labs to NovaTech where present",
            "System-role instructions excluded",
        ],
        "hr_review": "Selected answers inspected for internal consistency; legal and real-employer applicability not asserted",
        "it_documents": len(IT),
        "it_generation": {
            "generator": "OpenAI Codex assistant (interactive generation)",
            "model_revision": "not captured",
            "prompt_version": "option-c-v1",
            "review": "Reviewed as vendor-neutral fictional company procedures; no product-specific command sequences included",
        },
        "document_count": len(HR_IDS) + len(IT),
        "known_gaps": unknown,
    }
    (KB / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Prepared {len(HR_IDS)} HR documents, {len(IT)} IT documents, {len(cases)} evaluation cases"
    )


if __name__ == "__main__":
    main()
