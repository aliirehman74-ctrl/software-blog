import Link from "next/link";
import { getAllPosts } from "@/lib/posts";

export default function Home() {
  const posts = getAllPosts();

  return (
    <main className="mx-auto max-w-2xl px-5 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Software Reviews</h1>
      <p className="mt-2 text-neutral-600">
        Honest reviews, pricing and alternatives.
      </p>

      <ul className="mt-10 divide-y divide-neutral-200">
        {posts.map((p) => (
          <li key={p.slug} className="py-6">
            <Link href={`/posts/${p.slug}/`} className="group block">
              <h2 className="text-xl font-semibold group-hover:underline">
                {p.title}
              </h2>
              <p className="mt-1 text-neutral-600">{p.description}</p>
              <p className="mt-2 text-sm text-neutral-500">
                {p.date}
                {p.tags.length > 0 && ` · ${p.tags.join(", ")}`}
              </p>
            </Link>
          </li>
        ))}
        {posts.length === 0 && (
          <li className="py-6 text-neutral-500">No posts yet.</li>
        )}
      </ul>
    </main>
  );
}
