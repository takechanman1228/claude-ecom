# Site Audit Checks (SA01-SA15)

Site / landing page quality checks using Playwright headless browser.

## Check Definitions

### SA01 — CTA Above Fold (Desktop)
- **Severity:** Critical
- **What:** Checks if a Call-to-Action element (Buy Now, Add to Cart, Shop Now, etc.) is visible in the first viewport (above 1080px) on desktop.
- **Pass:** CTA element found with bounding box Y < 1080px
- **Fail:** No CTA found above fold
- **Why:** Users who don't see a CTA immediately are less likely to convert.

### SA02 — CTA Contrast & Size
- **Severity:** High
- **What:** Measures the largest CTA button's bounding box area.
- **Pass:** Area >= 3000px²
- **Warning:** Area >= 1500px²
- **Fail:** Area < 1500px² or no CTA found
- **Why:** Small or low-contrast CTAs get overlooked, reducing click-through.

### SA03 — Mobile CTA Visibility
- **Severity:** Critical
- **What:** Checks if a CTA is visible in the mobile viewport (375x812).
- **Pass:** CTA found with bounding box Y < 812px
- **Fail:** No CTA in mobile viewport
- **Why:** Mobile traffic often exceeds 60% for ecommerce; missing mobile CTA = lost sales.

### SA04 — Form Friction
- **Severity:** High
- **What:** Counts visible form fields (inputs, textareas, selects excluding hidden/submit).
- **Pass:** <= 5 fields
- **Warning:** 6-8 fields
- **Fail:** > 8 fields
- **Why:** Each additional form field reduces completion rate by ~5-10%.

### SA05 — Mobile Responsiveness
- **Severity:** Critical
- **What:** Checks for viewport meta tag and horizontal scroll on mobile.
- **Pass:** viewport meta present AND no horizontal scroll
- **Fail:** Missing viewport meta OR horizontal scroll detected
- **Why:** Non-responsive pages are unusable on mobile and penalized by Google.

### SA06 — Page Speed (LCP)
- **Severity:** High
- **What:** Measures Largest Contentful Paint on mobile viewport.
- **Pass:** LCP < 2500ms
- **Warning:** 2500-4000ms
- **Fail:** > 4000ms
- **Why:** Google Core Web Vitals threshold. Slow pages lose 53% of mobile visitors.

### SA07 — Layout Shift (CLS)
- **Severity:** Medium
- **What:** Measures Cumulative Layout Shift score.
- **Pass:** CLS < 0.1
- **Warning:** 0.1-0.25
- **Fail:** > 0.25
- **Why:** Layout shifts cause misclicks and user frustration.

### SA08 — Trust Signals
- **Severity:** High
- **What:** Checks for presence of reviews, testimonials, trust badges, and guarantees.
- **Pass:** >= 2 distinct trust signal types
- **Warning:** 1 type present
- **Fail:** No trust signals found
- **Why:** Trust signals increase CVR by 15-30% in ecommerce.

### SA09 — Schema Markup
- **Severity:** Medium
- **What:** Checks for structured data (JSON-LD) with relevant types.
- **Pass:** Product, FAQPage, Service, Organization, LocalBusiness, or BreadcrumbList found
- **Fail:** No relevant schema types
- **Why:** Schema enables rich snippets in search results, improving CTR.

### SA10 — Contact/Support Access
- **Severity:** Medium
- **What:** Checks for phone link, chat widget, or contact form.
- **Pass:** At least one contact channel found
- **Fail:** No contact channels
- **Why:** Accessible support reduces cart abandonment and builds trust.

### SA11 — H1 Heading Present
- **Severity:** High
- **What:** Checks if the page has an H1 heading.
- **Pass:** H1 element found with text content
- **Fail:** No H1 heading
- **Why:** H1 is critical for SEO and helps users confirm they're on the right page.

### SA12 — Image Count
- **Severity:** Medium
- **What:** Counts `<img>` elements on the page.
- **Pass:** 2-20 images
- **Warning:** 1 image or 21-30 images
- **Fail:** 0 images or > 30 images
- **Why:** Too few images lack visual appeal; too many slow the page.

### SA13 — Security Indicators
- **Severity:** Medium
- **What:** Checks HTTPS, payment badges, and privacy policy link.
- **Pass:** HTTPS + payment/privacy indicators
- **Warning:** HTTPS only
- **Fail:** Not HTTPS
- **Why:** Security signals are essential for ecommerce trust.

### SA14 — Navigation Consistency
- **Severity:** Medium
- **What:** Checks for nav/header element and logo linking to homepage.
- **Pass:** Nav present + logo links home
- **Warning:** Nav present, logo doesn't link home
- **Fail:** No navigation found
- **Why:** Consistent navigation reduces bounce rate and aids exploration.

### SA15 — Font Readability (Mobile)
- **Severity:** Low
- **What:** Measures the computed base font size on mobile viewport.
- **Pass:** >= 16px
- **Warning:** 14-15px
- **Fail:** < 14px
- **Why:** Small text on mobile hurts readability and accessibility.

## Multi-Page Aggregation

When crawling multiple pages:
- **Performance (SA06, SA07):** Uses worst-case (highest LCP, highest CLS)
- **Content quality (SA08, SA09, SA11):** Uses best-case (any page passing is sufficient)
- **CTA (SA01, SA03):** Any page having CTA counts as pass
- **Navigation (SA14):** All pages must have consistent navigation
- **Mobile (SA05, SA15):** All pages must be responsive

## CTA Selectors

Ecommerce-expanded selectors used for CTA detection:
- `Add to Cart`, `Buy Now`, `Shop Now`, `Order Now` (button text)
- `[class*='add-to-cart']`, `[class*='buy-now']`, `[data-action='add-to-cart']`
- `Get Started`, `Sign Up`, `Free Trial`, `Subscribe` (button text)
- `.cta`, `[class*='cta']`
- Links to signup, register, buy, demo, trial, contact paths
