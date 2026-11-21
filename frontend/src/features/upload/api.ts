import { useMutation, useQuery } from "@tanstack/react-query";
import { getConfig, submitJob } from "../../shared/api/client";

export const useConfig = () =>
  useQuery({ queryKey: ["config"], queryFn: getConfig, staleTime: Infinity });

export const useSubmitJob = () => useMutation({ mutationFn: submitJob });
