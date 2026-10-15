import ReactMarkdown from "react-markdown";

// Split out so the Markdown parser loads only when the first AI answer arrives.
export default function Markdown({ text }: { text: string }) {
  return <ReactMarkdown>{text}</ReactMarkdown>;
}
