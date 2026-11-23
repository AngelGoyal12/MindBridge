
import { apiRequest } from "./api";

export async function predictCaseCategory(title, description) {
  return apiRequest("/api/v1/ai/predict-category", {
    method: "POST",
    body: JSON.stringify({
      title,
      description,
    }),
  });
}
