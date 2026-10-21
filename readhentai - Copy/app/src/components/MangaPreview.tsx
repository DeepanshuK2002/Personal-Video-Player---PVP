import { CoverImage } from "@/components/CoverImage";

/** Horizontal strip of page thumbnails — always shown fully expanded. */
export function PreviewPages({ pages }: { pages: string[] }) {
  return (
    <div className="no-scrollbar mt-4 flex gap-3 overflow-x-auto">
      {pages.map((src, i) => (
        <CoverImage
          key={src}
          src={src}
          alt={`page ${i + 1}`}
          className="aspect-[3/4] w-40 shrink-0 rounded-lg"
        />
      ))}
    </div>
  );
}
