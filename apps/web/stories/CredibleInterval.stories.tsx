import type { Meta, StoryObj } from "@storybook/react";
import { CredibleInterval } from "@/components/domain/CredibleInterval";

const meta: Meta<typeof CredibleInterval> = {
  title: "Domain/CredibleInterval",
  component: CredibleInterval,
};
export default meta;
type Story = StoryObj<typeof CredibleInterval>;

export const Bar: Story = {
  args: {
    posterior: { mean: 8.3, lower: 7, upper: 9.4, nObservations: 60 },
    format: "bar",
  },
};
export const Inline: Story = {
  args: {
    posterior: { mean: 8.3, lower: 7, upper: 9.4, nObservations: 60 },
    format: "inline",
  },
};
export const Tuple: Story = {
  args: {
    posterior: { mean: 8.3, lower: 7, upper: 9.4, nObservations: 60 },
    format: "tuple",
  },
};
export const Weak: Story = {
  args: {
    posterior: { mean: 5, lower: 4, upper: 6, nObservations: 60 },
    status: "weak",
  },
};
