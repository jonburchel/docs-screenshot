# Microsoft Learn Screenshot Guidelines Reference

This document consolidates all official guidance for creating screenshots for Azure documentation
on learn.microsoft.com. Sources are internal Microsoft contributor guides (authenticated access required).

## Sources

1. [How to create screenshots for Azure content](https://learn.microsoft.com/en-us/help/get-started/add-azure-screenshot) (primary)
2. [Create a screenshot for documentation](https://learn.microsoft.com/en-us/help/contribute/contribute-how-to-create-screenshot) (general)
3. [Approved GUID and sensitive identifiers](https://learn.microsoft.com/en-us/help/platform/reference-sensitive-identifier) (PII replacement)
4. [Legal guidelines](https://learn.microsoft.com/en-us/help/contribute/contribute-legal-guidelines) (fictitious names, IPs, domains)
5. [Fictitious names, domains, and addresses](https://learn.microsoft.com/en-us/writing-style-guide-msft-internal/legal-content/fictitious-names-domains-and-addresses) (MS Writing Style Guide Internal)

## Key Rules

### Window & Browser
- Portal URL: `https://portal.azure.com/?feature.customportal=false`
- Window size: 1200 x 800 pixels (via Edge device emulation)
- First screenshot per article: full browser frame (URL bar + controls)
- Subsequent screenshots: focused view acceptable
- Use default Azure theme (dark blue sidebars)

### Callout Boxes
- Color: RGB **233, 28, 28**
- Thickness: **3px**
- Shape: Rectangle (box tool)
- Should hug the element closely
- Max 3-4 per screenshot

### PII Requirements
- ALL GUIDs must be replaced unless publicly known
- ALL emails must use approved fictitious domains
- ALL IPs must be from safe/reserved ranges
- Resource names should be generic (contoso-*, fabrikam-*)
- Subscription IDs always replaced
- Font for manual edits: **Segoe UI**

### File Format
- Format: PNG (.png lowercase)
- Naming: lowercase, letters/numbers/hyphens only, no spaces
- Pattern: `service-technology-image-description.png`
- Max width: 1200px
- Target size: under 200 KB
- Gray border required (1px, for light/dark theme contrast)

### Alt Text
- Descriptive, conveys purpose
- Ends with a period
- Example: "Screenshot of the virtual machines list showing the contoso-vm resource."

### Markdown Syntax
```markdown
:::image type="content" source="media/article-name/description.png" alt-text="Descriptive alt text.":::
```
