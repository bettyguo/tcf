import { FlatCompat } from "@eslint/eslintrc";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { createRequire } from "node:module";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const require = createRequire(import.meta.url);

const compat = new FlatCompat({ baseDirectory: __dirname });

// ADR-025 enforcement: NCLC values render through <CredibleInterval />,
// never as a bare literal. The rule lives in `eslint/no-bare-nclc.js`.
const noBareNclc = require("./eslint/no-bare-nclc.js");

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "out/**",
      "playwright-report/**",
      "test-results/**",
      "storybook-static/**",
    ],
  },
  {
    plugins: {
      "tcf-accel": {
        rules: {
          "no-bare-nclc": noBareNclc,
        },
      },
    },
    rules: {
      "tcf-accel/no-bare-nclc": "error",
    },
  },
];

export default config;
