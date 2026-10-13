import { useQuery } from "@tanstack/react-query";
import { useClient } from "../../auth/context";
import { data } from "../../shared/api";

export function useModelProviderDefinitions() {
  const client = useClient();
  return useQuery({
    queryKey: ["model-provider-types"],
    queryFn: ({ signal }) =>
      client.http
        .GET("/api/v1/provider-types/{kind}", {
          params: { path: { kind: "model" } },
          signal,
        })
        .then(data),
  });
}
