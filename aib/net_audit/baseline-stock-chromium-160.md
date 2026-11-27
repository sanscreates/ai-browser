# Net audit baseline: stock Chromium 160.0.8188.0 (same upstream commit)

Run 2026-11-27 with `aib/scripts/net_audit.sh ~/aib-build/stock-chromium/1756194/chrome-mac/Chromium.app --idle 300`: the official Chromium snapshot Mac_Arm/1756194, fresh profile, 5 minutes idle on the new tab page, then example.com, a Wikipedia article and MDN, then a SIGTERM shutdown.

`doh.xfinity.com` is this machine's own DNS resolver (Chromium's DoH upgrade of the system DNS), listed for completeness but not counted. `incoming.telemetry.mozilla.org` is MDN's own page telemetry (a subresource of a site we opened).

| host | idle | browse | top-frame sites | verdict |
|---|---|---|---|---|
| auth.wikimedia.org | 0 | 2 | https://wikipedia.org | visited site |
| clients2.google.com | 2 | 0 |  | UNSOLICITED (idle) |
| content-autofill.googleapis.com | 0 | 5 | https://wikipedia.org | UNSOLICITED (Google host) |
| developer.mozilla.org | 0 | 72 | https://mozilla.org | visited site |
| doh.xfinity.com | 12 | 20 |  | system DNS resolver (DoH) |
| edgedl.me.gvt1.com | 23 | 0 |  | UNSOLICITED (idle) |
| en.wikipedia.org | 0 | 27 | https://wikipedia.org | visited site |
| example.com | 0 | 5 | https://example.com | visited site |
| incoming.telemetry.mozilla.org | 0 | 6 | https://mozilla.org | visited site |
| meta.wikimedia.org | 0 | 1 | https://wikipedia.org | visited site |
| ogads-pa.clients6.google.com | 4 | 0 |  | UNSOLICITED (idle) |
| play.google.com | 4 | 0 |  | UNSOLICITED (idle) |
| safebrowsing.googleapis.com | 2 | 0 |  | UNSOLICITED (idle) |
| thumb.wikimedia.org | 0 | 4 | https://wikipedia.org | visited site |
| update.googleapis.com | 31 | 0 |  | UNSOLICITED (idle) |
| upload.wikimedia.org | 0 | 3 | https://wikipedia.org | visited site |
| www.google.com | 8 | 1 | https://google.com | UNSOLICITED (idle) |
| www.gstatic.com | 3 | 0 |  | UNSOLICITED (idle) |

unsolicited hosts: 9
  - clients2.google.com
  - content-autofill.googleapis.com
  - edgedl.me.gvt1.com
  - ogads-pa.clients6.google.com
  - play.google.com
  - safebrowsing.googleapis.com
  - update.googleapis.com
  - www.google.com
  - www.gstatic.com
