# azure-screenshot

A Copilot CLI skill that automates Azure portal screenshot capture for Microsoft Learn documentation. Handles browser automation, PII redaction with official Microsoft-approved fictitious values, callout boxes, cropping, and GIMP handoff.

## Prerequisites

- **Windows** with [Microsoft Edge](https://www.microsoft.com/edge)
- **Copilot CLI** with the [playwright-cli skill](https://github.com/anthropics/claude-code/tree/main/skills/playwright-cli) installed (`playwright-cli install --skills`)
- **Python 3.10+** with Pillow: `pip install Pillow`
- **Azure CLI**: `winget install Microsoft.AzureCLI` (for resource provisioning)
- **GIMP 2.10+** (optional, for final review): `winget install GIMP.GIMP`

## Install

### Option A: Clone and symlink (recommended)

```powershell
# Clone to wherever you keep tools
git clone https://github.com/jonburchel/azure-screenshot.git
cd azure-screenshot

# Create a junction so Copilot CLI discovers the skill
cmd /c mklink /J "%USERPROFILE%\.copilot\skills\azure-screenshot" "%CD%"
```

### Option B: Direct copy

```powershell
# Copy the skill directory
Copy-Item -Recurse .\azure-screenshot "$env:USERPROFILE\.copilot\skills\azure-screenshot"
```

### Verify installation

After installing, restart Copilot CLI. The skill should appear when you run:
```
/skills
```

You can also just ask: *"Take an Azure screenshot of the resource groups page"* and the skill will activate automatically.

## What it does

1. **Opens Azure portal** in Edge with your existing Microsoft SSO (persistent profile)
2. **Navigates** to the target page, dismisses popups/banners
3. **Provisions Azure resources** if needed (via `az` CLI)
4. **Scrubs PII** from the live DOM before capture, including cross-origin iframes
5. **Takes the screenshot** at 1200x800 (per contributor guide spec)
6. **Post-processes**: crop, callout boxes, gray border, PNG optimization
7. **Opens in GIMP** for final human review
8. **Reports**: lists all PII found, replacements made, image dimensions/size

## Key innovation: cross-origin iframe scrubbing

Azure portal renders grid/table content inside cross-origin iframes (`sandbox-*.reactblade.portal.azure.net`). Standard JavaScript cannot access these frames. This skill uses Playwright's `page.frames()` API to iterate *all* frames and scrub each one. Verified to produce 56+ replacements on a real portal page.

## PII replacement values

All replacement values come from the official Microsoft contributor guides:

| PII Type | Example Replacement |
|----------|-------------------|
| Subscription ID | `aaaa0a0a-bb1b-cc2c-dd3d-eeeeee4e4e4e` |
| Tenant ID | `aaaabbbb-0000-cccc-1111-dddd2222eeee` |
| Application ID | `00001111-aaaa-2222-bbbb-3333cccc4444` |
| Email | `john@contoso.com` |
| Tenant domain | `contoso.onmicrosoft.com` |
| Resource names | `contoso-rg`, `fabrikam-vm-01`, etc. |
| IP addresses | `192.168.1.15`, `198.51.100.101` |

Full reference: [Approved GUID and sensitive identifiers](https://learn.microsoft.com/en-us/help/platform/reference-sensitive-identifier)

## Callout boxes

Per the [Azure screenshot guide](https://learn.microsoft.com/en-us/help/get-started/add-azure-screenshot):

- Color: RGB **233, 28, 28**
- Thickness: **3px**
- Rectangles hug the target element closely

## Project structure

```
azure-screenshot/
├── SKILL.md                    # Copilot CLI skill definition (the brain)
├── README.md                   # This file
├── lib/
│   ├── dom_scrubber.py         # Frame-aware DOM PII replacement (preferred)
│   ├── pii_detector.py         # PII pattern matching + approved replacements
│   ├── image_editor.py         # Crop, redact, callout, border, optimize
│   ├── screenshot_processor.py # CLI orchestrator + report generation
│   ├── gimp_bridge.py          # GIMP integration
│   └── extract_dom_info.js     # DOM text extraction (Shadow DOM aware)
└── references/
    └── screenshot-guidelines.md # Consolidated MS contributor guide reference
```

## Supported PII patterns

- GUIDs/UUIDs (with context-aware classification: subscription, tenant, app, etc.)
- Email addresses (including `@microsoft.com` employee emails)
- Tenant domains (`*.onmicrosoft.com`)
- Public IP addresses (flags non-reserved IPs)
- Access keys, client secrets, thumbprints
- Custom text patterns (resource names, subscription names, usernames)

## Contributing

Found a bug or want to improve detection patterns? Open an issue or PR.

## References

- [How to create screenshots for Azure content](https://learn.microsoft.com/en-us/help/get-started/add-azure-screenshot)
- [Create a screenshot for documentation](https://learn.microsoft.com/en-us/help/contribute/contribute-how-to-create-screenshot)
- [Approved GUID and sensitive identifiers](https://learn.microsoft.com/en-us/help/platform/reference-sensitive-identifier)
- [Legal guidelines](https://learn.microsoft.com/en-us/help/contribute/contribute-legal-guidelines)
