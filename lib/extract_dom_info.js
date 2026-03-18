/**
 * extract_dom_info.js - DOM Text Extraction Payload
 * 
 * Run via: playwright-cli run-code "$(cat lib/extract_dom_info.js)"
 * Or inline via the skill's instructions.
 *
 * Walks every visible text node in the page, returns structured JSON with:
 * - text content
 * - bounding box (in CSS pixels and screenshot pixels)
 * - computed styles (font, size, color, background)
 * - element context (tag, classes, aria labels)
 */
async page => {
  return await page.evaluate(() => {
    const DPR = window.devicePixelRatio || 1;
    const results = [];

    // Get effective background color, walking up ancestors if transparent
    function getEffectiveBgColor(el) {
      let current = el;
      while (current && current !== document.documentElement) {
        const bg = getComputedStyle(current).backgroundColor;
        if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
          return bg;
        }
        current = current.parentElement || current.host;
      }
      return 'rgb(255, 255, 255)'; // default white
    }

    // Check if element is visible
    function isVisible(el) {
      if (!el || !el.getBoundingClientRect) return false;
      try {
        const style = getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      } catch(e) { return false; }
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return false;
      // Must be within viewport
      if (rect.bottom < 0 || rect.top > window.innerHeight) return false;
      if (rect.right < 0 || rect.left > window.innerWidth) return false;
      return true;
    }

    // Recursively walk DOM including Shadow DOM and iframes
    function walkNode(root) {
      const walker = document.createTreeWalker(
        root,
        NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
        {
          acceptNode: function(node) {
            if (node.nodeType === Node.TEXT_NODE) {
              const text = node.textContent.trim();
              if (!text) return NodeFilter.FILTER_REJECT;
              if (!isVisible(node.parentElement)) return NodeFilter.FILTER_REJECT;
              return NodeFilter.FILTER_ACCEPT;
            }
            // For elements, accept to traverse children
            return NodeFilter.FILTER_ACCEPT;
          }
        }
      );

      let node;
      while (node = walker.nextNode()) {
        // If element has shadow root, recurse into it
        if (node.nodeType === Node.ELEMENT_NODE) {
          if (node.shadowRoot) {
            walkNode(node.shadowRoot);
          }
          // Check for iframes
          if (node.tagName === 'IFRAME') {
            try {
              const iframeDoc = node.contentDocument || node.contentWindow.document;
              if (iframeDoc && iframeDoc.body) {
                walkNode(iframeDoc.body);
              }
            } catch(e) { /* cross-origin, skip */ }
          }
          continue;
        }

        // Text node processing
        const el = node.parentElement;
        if (!el) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        const rects = range.getClientRects();

        for (const rect of rects) {
          if (rect.width === 0 || rect.height === 0) continue;

          const text = node.textContent.trim();
          if (!text) continue;

          let style;
          try { style = getComputedStyle(el); } catch(e) { continue; }
          const bgColor = getEffectiveBgColor(el);

          results.push({
            text: text,
            // CSS pixel coordinates (relative to viewport)
            cssRect: {
              x: Math.round(rect.x * 100) / 100,
              y: Math.round(rect.y * 100) / 100,
              width: Math.round(rect.width * 100) / 100,
              height: Math.round(rect.height * 100) / 100,
            },
            // Screenshot pixel coordinates (CSS * DPR)
            pxRect: {
              x: Math.round(rect.x * DPR),
              y: Math.round(rect.y * DPR),
              width: Math.round(rect.width * DPR),
              height: Math.round(rect.height * DPR),
            },
            style: {
              fontFamily: style.fontFamily,
              fontSize: style.fontSize,
              fontWeight: style.fontWeight,
              color: style.color,
              backgroundColor: bgColor,
            },
            element: {
              tag: el.tagName.toLowerCase(),
              id: el.id || null,
              className: (typeof el.className === 'string') ? el.className : null,
              ariaLabel: el.getAttribute ? (el.getAttribute('aria-label') || null) : null,
            },
            dpr: DPR,
          });
        }
      }
    }

    // Start walking from body, plus any top-level shadow roots
    walkNode(document.body);

    // Also walk all elements with open shadow roots (belt and suspenders)
    document.querySelectorAll('*').forEach(el => {
      if (el.shadowRoot && el !== document.body) {
        walkNode(el.shadowRoot);
      }
    });

    return {
      url: window.location.href,
      title: document.title,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      dpr: DPR,
      timestamp: new Date().toISOString(),
      textNodes: results,
    };
  });
}
