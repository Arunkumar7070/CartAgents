import ReactMarkdown from "react-markdown";

const SAFE_URL = /^https:\/\//i;

export function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-2 text-[15px] leading-relaxed [&_li]:ml-4 [&_li]:list-disc [&_strong]:font-semibold">
      <ReactMarkdown
        disallowedElements={["img"]}
        urlTransform={(url) => (SAFE_URL.test(url) ? url : "")}
        components={{
          a: ({ href, children: label }) =>
            href ? (
              <a href={href} target="_blank" rel="noreferrer noopener" className="underline decoration-stamp">
                {label}
              </a>
            ) : (
              <span>{label}</span>
            ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
