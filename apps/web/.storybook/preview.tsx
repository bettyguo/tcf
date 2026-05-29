import type { Preview } from "@storybook/react";
import "../app/globals.css";
import { NextIntlClientProvider } from "next-intl";
import en from "../messages/en.json";

const preview: Preview = {
  parameters: {
    a11y: {
      // Storybook a11y addon — runs axe-core per story.
      element: "#storybook-root",
      manual: false,
    },
  },
  decorators: [
    (Story) => (
      <NextIntlClientProvider locale="en" messages={en}>
        <Story />
      </NextIntlClientProvider>
    ),
  ],
};

export default preview;
