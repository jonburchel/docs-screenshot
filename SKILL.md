---
name: azure-screenshot
description: Capture, process, and redact Azure portal screenshots for Microsoft Learn documentation. Use when the user needs to take Azure screenshots, redact PII, add callout boxes, crop images, or prepare documentation screenshots.
allowed-tools: Bash(playwright-cli:*), Bash(python:*), Bash(az:*)
---

# Azure Documentation Screenshot Skill

Automates the full pipeline for creating Azure portal screenshots that comply with Microsoft Learn contributor guidelines: browser automation, PII redaction with approved fictitious values, callout boxes, smart cropping, and GIMP handoff.

## Quick Start

```bash
# 1. Open Azure portal in Edge with persistent profile
playwright-cli open --browser=msedge --persistent "https://portal.azure.com/?feature.customportal=false"

# 2. Navigate to the target page
playwright-cli goto "https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Compute%2FVirtualMachines"

# 3. Wait for page to load, dismiss any popups
playwright-cli run-code "async page => { await page.waitForLoadState('networkidle'); }"

# 4. Take screenshot + extract DOM info simultaneously
playwright-cli screenshot --filename=raw-screenshot.png
# Then run the DOM extraction (see "Extract DOM Info" section below)

# 5. Process the image (PII redaction, callouts, crop, optimize)
python F:\home\azure-screenshot\lib\screenshot_processor.py \
  --dom-json dom_data.json --image raw-screenshot.png \
  --output processed-screenshot.png \
  --description "Virtual machines list in Azure portal"
```

## Full Workflow

### Phase 1: Azure Authentication & Setup

**Open browser with persistent Edge profile (picks up existing Microsoft SSO):**
```bash
playwright-cli open --browser=msedge --persistent "https://portal.azure.com/?feature.customportal=false"
```

The `?feature.customportal=false` flag hides internal/preview features that customers cannot see.

**Check if authenticated:**
```bash
playwright-cli snapshot
# Look for user avatar/name in the snapshot. If you see a sign-in button, auth is needed.
```

**If login is needed, prefer microsoft.com credentials:**
```bash
playwright-cli snapshot
# Find the email input field ref
playwright-cli fill <ref> "jburchel@microsoft.com"
playwright-cli click <submit-ref>
# Wait for redirect
playwright-cli run-code "async page => { await page.waitForLoadState('networkidle'); }"
```

**Select BAMI subscription if multiple subscriptions exist:**
```bash
# Navigate to subscription picker or use az CLI
playwright-cli goto "https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBladeV2"
playwright-cli snapshot
# Look for "BAMI" in the subscription list and select it
```

### Phase 2: Dismiss Popups & Banners

Azure portal frequently shows popups, preview banners, and welcome dialogs. Dismiss them all before taking screenshots.

```bash
# Common popup dismissal patterns
playwright-cli run-code "async page => {
  // Close 'Welcome' or 'What's new' dialogs
  const closeButtons = await page.locator('[aria-label=\"Close\"], [aria-label=\"Dismiss\"], button:has-text(\"Got it\"), button:has-text(\"Maybe later\"), button:has-text(\"Skip\"), button:has-text(\"No thanks\"), button:has-text(\"OK\"), .portal-banner-close, [data-telemetryname=\"DismissButton\"]').all();
  for (const btn of closeButtons) {
    try { await btn.click({ timeout: 1000 }); } catch(e) {}
  }
  // Close preview banners
  const previewBanners = await page.locator('[class*=\"preview-banner\"] button, [class*=\"fxs-banner\"] button').all();
  for (const btn of previewBanners) {
    try { await btn.click({ timeout: 1000 }); } catch(e) {}
  }
  // Wait for animations
  await page.waitForTimeout(500);
}"
```

**For persistent notification banners:**
```bash
playwright-cli run-code "async page => {
  // Hide notification panels via CSS
  await page.addStyleTag({ content: '.fxs-toast-container, .fxs-notification-panel { display: none !important; }' });
}"
```

### Phase 3: Azure Resource Provisioning

If the screenshot requires specific Azure resources to exist, create them using Azure CLI:

```bash
# Example: Create a resource group
az group create --name contoso-rg --location eastus

# Example: Create a VM
az vm create --resource-group contoso-rg --name contoso-vm \
  --image Ubuntu2204 --size Standard_B1s \
  --admin-username azureuser --generate-ssh-keys

# Example: Create a storage account
az storage account create --name contosostorageacct \
  --resource-group contoso-rg --location eastus --sku Standard_LRS
```

**IMPORTANT: Use fictitious-sounding names for resources** (contoso-*, fabrikam-*, etc.) so they appear correct in screenshots without needing redaction.

**After screenshots are complete, ASK the user whether to clean up:**
```bash
# List resources created
az group show --name contoso-rg --query "{name:name, location:location}"
# Ask user before deleting
az group delete --name contoso-rg --yes --no-wait
```

### Phase 4: Window Sizing & Screenshot Capture

**Set the browser to the standard documentation screenshot size (1200x800):**
```bash
playwright-cli resize 1200 800
```

**Wait for full page load:**
```bash
playwright-cli run-code "async page => {
  await page.waitForLoadState('networkidle');
  // Extra wait for Azure portal animations
  await page.waitForTimeout(2000);
}"
```

**Take the screenshot:**
```bash
playwright-cli screenshot --filename=raw-screenshot.png
```

### Phase 5: DOM Extraction for PII Detection

This is the key innovation. Instead of OCR, we extract text positions directly from the DOM, giving us pixel-perfect coordinates.

**Extract DOM info (save the output to a JSON file):**
```bash
playwright-cli run-code "async page => {
  return await page.evaluate(() => {
    const DPR = window.devicePixelRatio || 1;
    const results = [];
    function getEffectiveBgColor(el) {
      let current = el;
      while (current && current !== document.documentElement) {
        const bg = getComputedStyle(current).backgroundColor;
        if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') return bg;
        current = current.parentElement;
      }
      return 'rgb(255, 255, 255)';
    }
    function isVisible(el) {
      if (!el || !el.getBoundingClientRect) return false;
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return false;
      if (rect.bottom < 0 || rect.top > window.innerHeight) return false;
      if (rect.right < 0 || rect.left > window.innerWidth) return false;
      return true;
    }
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function(node) {
        const text = node.textContent.trim();
        if (!text) return NodeFilter.FILTER_REJECT;
        if (!isVisible(node.parentElement)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    let node;
    while (node = walker.nextNode()) {
      const el = node.parentElement;
      const range = document.createRange();
      range.selectNodeContents(node);
      const rects = range.getClientRects();
      for (const rect of rects) {
        if (rect.width === 0 || rect.height === 0) continue;
        const text = node.textContent.trim();
        if (!text) continue;
        const style = getComputedStyle(el);
        results.push({
          text: text,
          cssRect: { x: Math.round(rect.x*100)/100, y: Math.round(rect.y*100)/100, width: Math.round(rect.width*100)/100, height: Math.round(rect.height*100)/100 },
          pxRect: { x: Math.round(rect.x*DPR), y: Math.round(rect.y*DPR), width: Math.round(rect.width*DPR), height: Math.round(rect.height*DPR) },
          style: { fontFamily: style.fontFamily, fontSize: style.fontSize, fontWeight: style.fontWeight, color: style.color, backgroundColor: getEffectiveBgColor(el) },
          element: { tag: el.tagName.toLowerCase(), id: el.id || null, className: el.className || null },
          dpr: DPR,
        });
      }
    }
    return { url: window.location.href, title: document.title, viewport: { width: window.innerWidth, height: window.innerHeight }, dpr: DPR, timestamp: new Date().toISOString(), textNodes: results };
  });
}"
```

**Save the DOM extraction output** to a JSON file. The output from the run-code command contains the JSON under "### Result". Save it as `dom_data.json`.

### Phase 6: Image Processing

Use the screenshot processor to apply all transformations:

```bash
python F:\home\azure-screenshot\lib\screenshot_processor.py \
  --dom-json dom_data.json \
  --image raw-screenshot.png \
  --output my-final-screenshot.png \
  --description "Description of what this screenshot shows" \
  --callouts '[{"x": 100, "y": 200, "width": 300, "height": 50}]' \
  --crop-focus '[{"x": 50, "y": 150, "width": 400, "height": 300}]'
```

**Options:**
- `--skip-pii`: Skip PII detection/redaction
- `--skip-crop`: Skip smart cropping
- `--skip-border`: Skip gray border
- `--no-gimp`: Don't open in GIMP
- `--callouts`: JSON array of rectangles for red callout boxes
- `--crop-focus`: JSON array of rectangles defining area of interest

### Phase 7: Pre-Screenshot DOM Scrubbing (PREFERRED Method)

The most reliable approach is to replace PII directly in the DOM BEFORE taking the screenshot. This is the same approach as Microsoft's Screenshot Scrubber extension.

**CRITICAL: Azure portal uses cross-origin iframes** (`sandbox-*.reactblade.portal.azure.net`) for grid/table content. Standard `document.querySelectorAll` CANNOT reach them. You MUST use `page.frames()` to iterate all frames.

**Use the dom_scrubber.py module to generate the scrub script:**
```bash
python -c "
from F_home_azure_screenshot.lib.dom_scrubber import generate_scrub_js
js = generate_scrub_js(
    username='jburchel',
    subscription_name='jburchel BAMI subscription',
    tenant_display_name='Microsoft Customer Led',
    custom_replacements={
        'my-real-rg': 'contoso-rg',
        'DefaultResourceGroup-EUS': 'contoso-default-eus',
    },
)
with open('temp_scrub.js', 'w') as f:
    f.write(js)
"
playwright-cli run-code "$(cat temp_scrub.js)"
```

**Or inline, using the frame-aware pattern:**
```bash
playwright-cli run-code "async page => {
  const rules = [
    {isRegex: true, pattern: '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', flags: 'gi', replacement: 'aaaa0a0a-bb1b-cc2c-dd3d-eeeeee4e4e4e'},
    {isRegex: true, pattern: 'jburchel', flags: 'gi', replacement: 'john'},
    {isRegex: false, pattern: 'BAMI subscription', replacement: 'Contoso subscription'},
    // Add more rules as needed
  ];
  const frames = page.frames();
  let total = 0;
  for (const frame of frames) {
    try {
      const count = await frame.evaluate((r) => {
        let replaced = 0;
        function walk(root) {
          const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null);
          let n; const textNodes = [];
          while (n = w.nextNode()) {
            if (n.nodeType === 1) {
              if (n.shadowRoot) walk(n.shadowRoot);
              continue;
            }
            textNodes.push(n);
          }
          for (const tn of textNodes) {
            let t = tn.textContent; let changed = false;
            for (const rule of r) {
              let nt = rule.isRegex
                ? t.replace(new RegExp(rule.pattern, rule.flags), rule.replacement)
                : t.split(rule.pattern).join(rule.replacement);
              if (nt !== t) { t = nt; changed = true; }
            }
            if (changed) { tn.textContent = t; replaced++; }
          }
        }
        walk(document.body);
        document.querySelectorAll('*').forEach(el => { if (el.shadowRoot) walk(el.shadowRoot); });
        return replaced;
      }, rules);
      total += count;
    } catch(e) {}
  }
  return { framesProcessed: frames.length, totalReplaced: total };
}"
```

**Why this approach is preferred:**
1. The browser renders replacement text natively in Segoe UI at the correct size
2. No pixel-level font matching needed
3. Handles cross-origin iframes that pixel-level approaches cannot detect
4. The screenshot is "clean" from the start
5. Verified to produce 56+ replacements on a real Azure portal page

### Phase 8: Callout Boxes

For callout boxes, you need the pixel coordinates of the UI element to highlight. Get these from the DOM extraction:

```bash
# Find the element you want to highlight
playwright-cli snapshot
# Note the ref of the element (e.g., e15)

# Get its bounding box
playwright-cli run-code "async page => {
  const el = page.locator('[data-ref=\"e15\"]');
  const box = await el.boundingBox();
  return box;  // {x, y, width, height}
}"
```

Then pass those coordinates to the processor's `--callouts` argument, or draw them with the image_editor directly.

**Callout specifications (per Microsoft contributor guide):**
- Color: RGB **233, 28, 28** (hex #E91C1C)
- Border thickness: **3px**
- Rectangle should "hug" the element with 4px padding
- Maximum 3-4 callouts per screenshot
- Use numbered callouts for sequential steps if needed

### Phase 9: Final Review in GIMP

The processor automatically opens the result in GIMP. In GIMP, the user should:
1. Verify PII is fully redacted
2. Check callout placement
3. Adjust crop if needed
4. Verify the image looks natural and professional
5. Export as PNG (File > Export As > .png)

**GIMP location:** `C:\Program Files\GIMP 2\bin\gimp-2.10.exe`

If GIMP is already open, images open in the existing window.

### Phase 10: Summary Report

After processing, the skill outputs a summary:
- Image dimensions and file size
- Number of PII items detected and redacted
- Each PII item: original value, type, severity, replacement value, pixel location
- Number of callout boxes drawn
- Whether cropping was applied

---

## PII Replacement Reference

### Approved GUIDs (from MS Sensitive Identifiers Reference)

| Type | Example Approved Value |
|------|----------------------|
| Application (client) ID | `00001111-aaaa-2222-bbbb-3333cccc4444` |
| Certificate ID (SEV 0) | `0a0a0a0a-1111-bbbb-2222-3c3c3c3c3c3c` |
| Correlation ID | `aaaa0000-bb11-2222-33cc-444444dddddd` |
| Directory (tenant) ID | `aaaabbbb-0000-cccc-1111-dddd2222eeee` |
| Object ID | `aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb` |
| Principal ID | `aaaaaaaa-bbbb-cccc-1111-222222222222` |
| Resource ID | `a0a0a0a0-bbbb-cccc-dddd-e1e1e1e1e1e1` |
| Secret ID/Key ID (SEV 0) | `aaaaaaaa-0b0b-1c1c-2d2d-333333333333` |
| Subscription ID | `aaaa0a0a-bb1b-cc2c-dd3d-eeeeee4e4e4e` |
| Trace ID | `0000aaaa-11bb-cccc-dd22-eeeeee333333` |

### Approved Non-GUID Values

| Type | Example |
|------|---------|
| Client Secret | `Aa1Bb~2Cc3.-Dd4Ee5Ff6Gg7Hh8Ii9_Jj0Kk1Ll2` |
| Alphanumeric | `A1bC2dE3fH4iJ5kL6mN7oP8qR9sT0u` |
| Thumbprint | `AA11BB22CC33DD44EE55FF66AA77BB88CC99DD00` |
| Signature Hash | `aB1cD2eF-3gH4iJ5kL6-mN7oP8qR=` |

### Approved Fictitious Names (CELA-approved)

| Category | Approved Values |
|----------|----------------|
| Company domains | `contoso.com`, `fabrikam.com`, `northwindtraders.com`, `adventure-works.com` |
| Generic domains | `example.com`, `example.org`, `example.net` |
| Email format | First name only: `john@contoso.com` (NOT `john.smith@contoso.com`) |
| Resource groups | `contoso-rg`, `fabrikam-rg`, `myresourcegroup` |
| VMs | `contoso-vm`, `fabrikam-vm-01`, `myVM` |
| Storage accounts | `contosostorageacct`, `fabrikamstorage` |
| Key vaults | `contoso-kv`, `fabrikam-keyvault` |

### Safe IP Ranges for Documentation

- Private: `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`
- RFC 5737: `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`
- Azure wire server: `168.63.129.16`
- Loopback: `127.0.0.0/8`
- Link-local: `169.254.0.0/16`

---

## Image Requirements Checklist

- [ ] PNG format, lowercase `.png` extension
- [ ] Filename: lowercase, letters/numbers/hyphens only (no spaces)
- [ ] Max width: 1200px
- [ ] Target size: under 200 KB
- [ ] Gray border added (automatic with processor)
- [ ] First screenshot in article: full browser frame (URL bar + controls)
- [ ] Default Azure theme (dark blue sidebars, blue background)
- [ ] `?feature.customportal=false` in portal URL
- [ ] All PII replaced with approved fictitious values
- [ ] Callout boxes: RGB 233,28,28, 3px thickness
- [ ] Alt text prepared (descriptive, ends with period)
- [ ] Image naming follows: `service-technology-image-description.png`

---

## Common Azure Portal Popup Patterns

These are elements you'll frequently need to dismiss:

| Popup Type | Selector Pattern |
|-----------|-----------------|
| Welcome dialog | `button:has-text("Got it")`, `button:has-text("Maybe later")` |
| Preview banner | `[class*="preview-banner"] button`, `[class*="fxs-banner"] button` |
| Notification toast | `.fxs-toast-container button` |
| What's new | `button:has-text("What's new")` parent close button |
| Feature announcement | `[data-telemetryname="DismissButton"]` |
| Generic close | `[aria-label="Close"]`, `[aria-label="Dismiss"]` |
| Consent/cookie | `button:has-text("Accept")`, `button:has-text("OK")` |

---

## Lib Module Reference

All Python modules are at `F:\home\azure-screenshot\lib\`:

- **`screenshot_processor.py`**: Main orchestrator. CLI interface for full pipeline.
- **`pii_detector.py`**: Regex-based PII detection with context-aware GUID classification. All approved replacement values built in.
- **`image_editor.py`**: Pillow/OpenCV operations: crop, redact, callout, border, optimize.
- **`dom_scrubber.py`**: Frame-aware DOM PII replacement. Generates JS that uses `page.frames()` to scrub ALL frames including cross-origin Azure portal iframes. **This is the preferred pre-screenshot approach.**
- **`gimp_bridge.py`**: GIMP integration (detect running instance, open images).
- **`extract_dom_info.js`**: JavaScript payload for `playwright-cli run-code` DOM extraction (Shadow DOM aware).
