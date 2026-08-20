import { compareRegimes, defaultProfile, mergeProfile } from "@/lib/taxEngine";
import type { TaxProfile } from "@/lib/types";

export async function POST(request: Request) {
  const body = (await request.json()) as { profile?: Partial<TaxProfile> };
  const profile = mergeProfile(defaultProfile(), body.profile ?? {});
  const advice = compareRegimes(profile);
  return Response.json({ advice });
}
