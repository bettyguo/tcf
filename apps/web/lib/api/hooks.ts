// Typed TanStack Query hooks per phase8_design.md §5.

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import { qk } from "./keys";
import type {
  TodayPayload,
  ReadinessSummary,
  SkillState,
  MockReportPayload,
  Skill,
} from "@/lib/types";

const ONE_MINUTE = 60 * 1000;

export function useToday() {
  return useQuery({
    queryKey: qk.todayBlocks(),
    queryFn: () => api.get("/plan/today") as Promise<TodayPayload>,
    staleTime: ONE_MINUTE,
  });
}

export function useReadiness() {
  return useQuery({
    queryKey: qk.readiness(),
    queryFn: () => api.get("/insights/readiness") as Promise<ReadinessSummary>,
    staleTime: ONE_MINUTE,
  });
}

export function useSkill(skill: Skill) {
  return useQuery({
    queryKey: qk.skill(skill),
    queryFn: () =>
      api.get(`/insights/skills/${skill}`) as Promise<SkillState>,
    staleTime: ONE_MINUTE,
  });
}

export function useInsightsOverview() {
  return useQuery({
    queryKey: qk.insights(),
    queryFn: () =>
      api.get("/insights") as Promise<{ skills: SkillState[]; target: number }>,
    staleTime: ONE_MINUTE,
  });
}

export function useMockReport(id: string) {
  return useQuery({
    queryKey: qk.mockReport(id),
    queryFn: () =>
      api.get(`/mock-exam/${id}/report`) as Promise<MockReportPayload>,
    staleTime: Infinity,
  });
}

export interface AcceptPlanInput {
  targetNclc: number;
  examDate?: string;
  dailyBudgetMin: number;
  l1?: string;
}

export function useAcceptPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AcceptPlanInput) => api.post("/plan/accept", input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.plan() });
      void qc.invalidateQueries({ queryKey: qk.todayBlocks() });
    },
  });
}

export function useStartMock(mode: "canonical" | "training") {
  return useMutation({
    mutationFn: () =>
      api.post("/mock-exam/start", { mode }) as Promise<{ id: string }>,
  });
}

export function useSubmitMockAnswer(mockId: string) {
  return useMutation({
    mutationFn: (input: { itemId: string; answer: unknown }) =>
      api.post(`/mock-exam/${mockId}/answer`, input),
  });
}
