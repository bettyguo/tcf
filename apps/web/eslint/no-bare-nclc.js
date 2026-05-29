// Custom ESLint rule (ADR-025 enforcement): JSX text literals containing
// a bare "NCLC <n>" pattern outside of `<CredibleInterval />` or i18n
// messages indicate a point estimate without a credible interval and
// MUST be replaced with the component or a `t("ci.nclcLabel")` call.
//
// Configured in eslint.config.mjs via `--rulesdir`-style include.
// Tested by tests/unit/eslint-no-bare-nclc.test.ts.

const PATTERN = /\bNCLC\s+\d/;

module.exports = {
  meta: {
    type: "problem",
    docs: {
      description:
        "ADR-025: NCLC values must render through <CredibleInterval /> or t('ci.nclcLabel').",
    },
    schema: [],
    messages: {
      bare:
        "Bare 'NCLC <n>' in JSX text. Use <CredibleInterval posterior={...} /> or t('ci.nclcLabel') instead.",
    },
  },
  create(context) {
    return {
      JSXText(node) {
        if (PATTERN.test(node.value)) {
          context.report({ node, messageId: "bare" });
        }
      },
      Literal(node) {
        if (typeof node.value === "string" && PATTERN.test(node.value)) {
          // Allow inside known-safe paths: the CredibleInterval source file
          // itself, the messages catalog, and Storybook fixtures.
          const filename = context.getFilename().replace(/\\/g, "/");
          if (
            filename.includes("/components/domain/CredibleInterval") ||
            filename.includes("/messages/") ||
            filename.includes("/stories/")
          ) return;
          context.report({ node, messageId: "bare" });
        }
      },
    };
  },
};
