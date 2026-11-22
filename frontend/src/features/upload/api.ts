import { useMutation, useQuery } from "@tanstack/react-query";
import { getConfig, submitBatch } from "../../shared/api/client";

export const useConfig = () =>
  useQuery({ queryKey: ["config"], queryFn: getConfig, staleTime: Infinity });

export const useSubmitBatch = () => useMutation({ mutationFn: submitBatch });
