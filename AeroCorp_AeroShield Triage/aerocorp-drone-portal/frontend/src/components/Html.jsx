export default function Html({ value, as: Tag = "span", className = "" }) {
  return <Tag className={className} dangerouslySetInnerHTML={{ __html: value ?? "" }} />;
}
