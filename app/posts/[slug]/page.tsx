import Link from "next/link";
import type { Metadata } from "next";
import { getAllPosts, getPost } from "@/lib/posts";

export const dynamicParams = false;

export function generateStaticParams() {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const { meta } = await getPost(slug);
  return { title: meta.title, description: meta.description };
}

export default async function PostPage({ params }: Props) {
  const { slug } = await params;
  const { meta, html } = await getPost(slug);

  return (
    <main className="mx-auto max-w-2xl px-5 py-12">
      <Link href="/" className="text-sm text-neutral-500 hover:underline">
        ← All reviews
      </Link>
      <h1 className="mt-4 text-3xl font-bold tracking-tight">{meta.title}</h1>
      <p className="mt-2 text-sm text-neutral-500">
        {meta.date}
        {meta.tags.length > 0 && ` · ${meta.tags.join(", ")}`}
      </p>
      <article
        className="prose prose-neutral mt-8 max-w-none"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </main>
  );
}
