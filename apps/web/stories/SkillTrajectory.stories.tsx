import type { Meta, StoryObj } from "@storybook/react";
import { SkillTrajectory } from "@/components/domain/SkillTrajectory";

const meta: Meta<typeof SkillTrajectory> = {
  title: "Domain/SkillTrajectory",
  component: SkillTrajectory,
};
export default meta;
type Story = StoryObj<typeof SkillTrajectory>;

const history = Array.from({ length: 8 }).map((_, i) => ({
  at: new Date(Date.now() - (7 - i) * 7 * 86400000).toISOString(),
  posterior: {
    mean: 6.2 + i * 0.22,
    lower: 5.3 + i * 0.22,
    upper: 7.4 + i * 0.22,
    nObservations: 5 + i * 4,
  },
}));

export const Full: Story = {
  args: { skill: "EE", history, target: 9, width: 480, height: 160 },
};
export const Sparkline: Story = {
  args: { skill: "EE", history, target: 9, width: 160, height: 40 },
};
