# components/aib

AI Browser's own `base::Feature`s, exposed in chrome://flags. They are
grouped by area: `aib_ui_features.h` (browser UI) and `aib_net_features.h`
(network and privacy). Blink-side features live in
`third_party/blink/public/common/aib_features.h`, because Blink can't
depend on //components.
