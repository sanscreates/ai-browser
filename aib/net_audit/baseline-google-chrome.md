# Net audit baseline: stock Google Chrome 158.0.8127.38

Run 2026-11-27 with `aib/scripts/net_audit.sh "/Applications/Google Chrome.app" --idle 30` (fresh profile; 30 s idle, then example.com, Wikipedia, MDN). For comparison only; our target is zero unsolicited hosts.

| host | idle | browse | top-frame sites | verdict |
|---|---|---|---|---|
| accounts.google.com | 3 | 0 | https://google.com | UNSOLICITED (idle) |
| auth.wikimedia.org | 0 | 3 | https://wikipedia.org | visited site |
| clients2.google.com | 4 | 0 | https://google.com | UNSOLICITED (idle) |
| clients2.googleusercontent.com | 3 | 0 | https://googleusercontent.com | UNSOLICITED (idle) |
| clientservices.googleapis.com | 3 | 0 |  | UNSOLICITED (idle) |
| content-autofill.googleapis.com | 0 | 6 | https://wikipedia.org | page subresource |
| developer.mozilla.org | 0 | 146 | https://mozilla.org | visited site |
| doh.xfinity.com | 11 | 42 |  | UNSOLICITED (idle) |
| edgedl.me.gvt1.com | 2 | 0 |  | UNSOLICITED (idle) |
| en.wikipedia.org | 0 | 74 | https://wikipedia.org | visited site |
| example.com | 0 | 6 | https://example.com | visited site |
| incoming.telemetry.mozilla.org | 0 | 11 | https://mozilla.org | visited site |
| meta.wikimedia.org | 0 | 4 | https://wikipedia.org | visited site |
| ogads-pa.clients6.google.com | 6 | 0 |  | UNSOLICITED (idle) |
| optimizationguide-pa.googleapis.com | 3 | 0 |  | UNSOLICITED (idle) |
| play.google.com | 3 | 0 |  | UNSOLICITED (idle) |
| redirector.gvt1.com | 2 | 0 | http://gvt1.com | UNSOLICITED (idle) |
| rr15---sn-bvvbaxivnuxqjvhj5nu-n4vl.gvt1.com | 2 | 0 | http://gvt1.com | UNSOLICITED (idle) |
| safebrowsing.googleapis.com | 0 | 3 |  | UNSOLICITED (browser-initiated) |
| thumb.wikimedia.org | 0 | 9 | https://wikipedia.org | visited site |
| update.googleapis.com | 3 | 0 |  | UNSOLICITED (idle) |
| upload.wikimedia.org | 0 | 4 | https://wikipedia.org | visited site |
| www.google.com | 16 | 5 | https://google.com | UNSOLICITED (idle) |
| www.gstatic.com | 7 | 0 |  | UNSOLICITED (idle) |

unsolicited hosts: 15
  - accounts.google.com
  - clients2.google.com
  - clients2.googleusercontent.com
  - clientservices.googleapis.com
  - doh.xfinity.com
  - edgedl.me.gvt1.com
  - ogads-pa.clients6.google.com
  - optimizationguide-pa.googleapis.com
  - play.google.com
  - redirector.gvt1.com
  - rr15---sn-bvvbaxivnuxqjvhj5nu-n4vl.gvt1.com
  - safebrowsing.googleapis.com
  - update.googleapis.com
  - www.google.com
  - www.gstatic.com
