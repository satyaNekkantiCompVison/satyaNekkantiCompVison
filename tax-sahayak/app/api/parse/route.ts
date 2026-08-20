import { extractText, getDocumentProxy } from "unpdf";
import { parseTaxDocument } from "@/lib/parseDocument";
import { compareRegimes } from "@/lib/taxEngine";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const form = await request.formData();
  const file = form.get("file");
  const pasted = String(form.get("text") ?? "");

  let text = pasted;
  if (file instanceof File) {
    const buffer = new Uint8Array(await file.arrayBuffer());
    const name = file.name.toLowerCase();
    if (name.endsWith(".pdf") || file.type === "application/pdf") {
      const pdf = await getDocumentProxy(buffer);
      const extracted = await extractText(pdf, { mergePages: true });
      text = Array.isArray(extracted.text) ? extracted.text.join("\n") : extracted.text;
    } else {
      text = new TextDecoder().decode(buffer);
    }
  }

  if (!text.trim()) {
    return Response.json({ error: "Upload a Form 16 / CTC PDF or paste the text." }, { status: 400 });
  }

  const profile = parseTaxDocument(text);
  const advice = compareRegimes(profile);
  return Response.json({ profile, advice, extractedLength: text.length });
}
