import { useQuery } from "@tanstack/react-query";
import { getFormSchema, getPreviewPdf } from "../../shared/api/client";

// The schema never changes while the app runs, so it is fetched once per session.
// Raw on purpose: review.ts (and CodeMirror with it) stays in the lazy review chunk; the screen applies K-09.
export const useFormSchema = () =>
  useQuery({
    queryKey: ["form-schema"],
    queryFn: getFormSchema,
    staleTime: Infinity,
  });

// One conversion per job and tab: the file never changes, and a failed one will not get better.
export const usePreviewPdf = (jobId: string, file: File) =>
  useQuery({
    queryKey: ["preview-pdf", jobId],
    queryFn: () => getPreviewPdf(file),
    staleTime: Infinity,
    retry: false,
  });
