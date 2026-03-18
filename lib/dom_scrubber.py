"""
dom_scrubber.py - Pre-Screenshot DOM PII Replacement

Generates JavaScript to replace PII directly in the browser DOM
BEFORE taking a screenshot. This is the most reliable approach because:
1. The browser renders replacement text natively in the correct font
2. No pixel-level font matching needed
3. Works regardless of Shadow DOM, canvas, etc.

This is the approach used by Microsoft's Screenshot Scrubber extension.
"""

import re
import json

# PII patterns and their replacements
DEFAULT_SCRUB_RULES = {
    # GUIDs -> approved replacement
    'guid': {
        'pattern': r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        'replacement': 'aaaa0a0a-bb1b-cc2c-dd3d-eeeeee4e4e4e',
        'flags': 'gi',
    },
    # Email addresses -> approved fictitious
    'email': {
        'pattern': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'replacement': 'john@contoso.com',
        'flags': 'gi',
    },
    # onmicrosoft.com tenant domains
    'tenant_domain': {
        'pattern': r'[A-Za-z0-9-]+\.onmicrosoft\.com',
        'replacement': 'contoso.onmicrosoft.com',
        'flags': 'gi',
    },
}


def generate_scrub_js(
    custom_replacements: dict[str, str] = None,
    username: str = None,
    subscription_name: str = None,
    tenant_display_name: str = None,
    include_default_rules: bool = True,
) -> str:
    """
    Generate JavaScript that scrubs PII from ALL frames (including cross-origin).
    
    CRITICAL: Azure portal renders grid content in cross-origin iframes
    (sandbox-*.reactblade.portal.azure.net). Standard document.querySelectorAll
    cannot reach them. This function generates code that uses Playwright's
    page.frames() API to iterate ALL frames and scrub each one.
    
    Args:
        custom_replacements: Dict of {find_text: replace_text} for exact string replacements
        username: If provided, replaces all occurrences (e.g., 'jburchel' -> 'john')
        subscription_name: If provided, replaces subscription display name
        tenant_display_name: If provided, replaces tenant/directory display name
        include_default_rules: Whether to include GUID/email/tenant regex replacements
        
    Returns:
        JavaScript string to execute via playwright-cli run-code
    """
    js_parts = []
    
    # Use page.frames() to iterate ALL frames including cross-origin iframes.
    # This is essential for Azure portal where grid content lives in
    # sandbox-*.reactblade.portal.azure.net cross-origin frames.
    js_parts.append("""
async page => {
  const rules = RULES_PLACEHOLDER;
  const frames = page.frames();
  let totalReplaced = 0;
  for (const frame of frames) {
    try {
      const count = await frame.evaluate((r) => {
        let replaced = 0;
        function walk(root) {
          const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null);
          let n;
          const textNodes = [];
          while (n = w.nextNode()) {
            if (n.nodeType === 1) {
              if (n.shadowRoot) walk(n.shadowRoot);
              ['title', 'placeholder', 'aria-label', 'value'].forEach(a => {
                const v = n.getAttribute(a);
                if (v) {
                  let nv = v;
                  for (const rule of r) {
                    if (rule.isRegex) {
                      nv = nv.replace(new RegExp(rule.pattern, rule.flags), rule.replacement);
                    } else {
                      nv = nv.split(rule.pattern).join(rule.replacement);
                    }
                  }
                  if (nv !== v) { n.setAttribute(a, nv); replaced++; }
                }
              });
              if (n.tagName === 'INPUT' || n.tagName === 'TEXTAREA') {
                let val = n.value || '';
                for (const rule of r) {
                  if (rule.isRegex) {
                    val = val.replace(new RegExp(rule.pattern, rule.flags), rule.replacement);
                  } else {
                    val = val.split(rule.pattern).join(rule.replacement);
                  }
                }
                n.value = val;
              }
              continue;
            }
            textNodes.push(n);
          }
          for (const tn of textNodes) {
            let t = tn.textContent;
            let changed = false;
            for (const rule of r) {
              let nt;
              if (rule.isRegex) {
                nt = t.replace(new RegExp(rule.pattern, rule.flags), rule.replacement);
              } else {
                nt = t.split(rule.pattern).join(rule.replacement);
              }
              if (nt !== t) { t = nt; changed = true; }
            }
            if (changed) { tn.textContent = t; replaced++; }
          }
        }
        walk(document.body);
        document.querySelectorAll('*').forEach(el => { if (el.shadowRoot) walk(el.shadowRoot); });
        return replaced;
      }, r);
      totalReplaced += count;
    } catch(e) { /* frame may be navigating */ }
  }
  return { framesProcessed: frames.length, totalReplaced };
}
""")
    
    # Build rules array
    rules = []
    
    if include_default_rules:
        for name, rule in DEFAULT_SCRUB_RULES.items():
            rules.append({
                'isRegex': True,
                'pattern': rule['pattern'],
                'flags': rule['flags'],
                'replacement': rule['replacement'],
            })
    
    # Username replacement (exact string, case-insensitive)
    if username:
        rules.append({
            'isRegex': True,
            'pattern': re.escape(username),
            'flags': 'gi',
            'replacement': 'john',
        })
    
    # Subscription name replacement
    if subscription_name:
        rules.append({
            'isRegex': False,
            'pattern': subscription_name,
            'replacement': 'Contoso subscription',
        })
    
    # Tenant display name replacement
    if tenant_display_name:
        rules.append({
            'isRegex': True,
            'pattern': re.escape(tenant_display_name),
            'flags': 'gi',
            'replacement': 'Contoso',
        })
    
    # Custom exact-string replacements
    if custom_replacements:
        for find_text, replace_text in custom_replacements.items():
            rules.append({
                'isRegex': False,
                'pattern': find_text,
                'replacement': replace_text,
            })
    
    # Inject rules into the JS
    rules_json = json.dumps(rules)
    js = '\n'.join(js_parts).replace('RULES_PLACEHOLDER', rules_json)
    
    return js


def generate_scrub_command(
    username: str = None,
    subscription_name: str = None,
    custom_replacements: dict[str, str] = None,
) -> str:
    """
    Generate a playwright-cli run-code command string for DOM scrubbing.
    
    Returns a string suitable for direct execution.
    """
    js = generate_scrub_js(
        username=username,
        subscription_name=subscription_name,
        custom_replacements=custom_replacements,
    )
    # For CLI usage, we need to escape for shell
    return js


if __name__ == '__main__':
    # Demo: generate scrub JS for a typical Azure scenario
    js = generate_scrub_js(
        username='jburchel',
        subscription_name='jburchel BAMI subscription',
        custom_replacements={
            'content-work-rg': 'contoso-rg',
            'rg-jburchel': 'rg-contoso',
            'NetworkWatcherRG': 'contoso-networkwatcher-rg',
            'operationsunrise-rg': 'fabrikam-rg',
            'jukullam-content-rg': 'northwind-rg',
        },
    )
    print("Generated scrub JS:")
    print(f"Length: {len(js)} chars")
    print(f"First 200 chars: {js[:200]}")
    print("\nThis JS should be run via: playwright-cli run-code \"<js>\"")
    print("BEFORE taking the screenshot.")
