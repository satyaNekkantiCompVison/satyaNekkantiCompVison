import { answerChat } from "@/lib/chatbot";
import { defaultProfile, mergeProfile } from "@/lib/taxEngine";
import type { ChatMessage, TaxProfile } from "@/lib/types";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    message?: string;
    history?: ChatMessage[];
    profile?: Partial<TaxProfile>;
  };
  const message = (body.message ?? "").trim();
  if (!message) {
    return Response.json({ error: "Type a question." }, { status: 400 });
  }
  const profile = mergeProfile(defaultProfile(), body.profile ?? {});
  const history = body.history ?? [];
  const reply = answerChat(message, history, profile);
  return Response.json({ reply });
}
