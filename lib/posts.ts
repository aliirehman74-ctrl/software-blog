import fs from "fs";
import path from "path";
import matter from "gray-matter";
import { remark } from "remark";
import remarkGfm from "remark-gfm";
import html from "remark-html";

const postsDir = path.join(process.cwd(), "posts");

export type PostMeta = {
  slug: string;
  title: string;
  description: string;
  date: string;
  tags: string[];
};

function readPost(file: string) {
  const slug = file.replace(/\.mdx?$/, "");
  const raw = fs.readFileSync(path.join(postsDir, file), "utf8");
  const { data, content } = matter(raw);
  const meta: PostMeta = {
    slug,
    title: String(data.title ?? slug),
    description: String(data.description ?? ""),
    date: data.date ? new Date(data.date).toISOString().slice(0, 10) : "",
    tags: Array.isArray(data.tags) ? data.tags.map(String) : [],
  };
  return { meta, content };
}

export function getAllPosts(): PostMeta[] {
  if (!fs.existsSync(postsDir)) return [];
  return fs
    .readdirSync(postsDir)
    .filter((f) => /\.mdx?$/.test(f))
    .map((f) => readPost(f).meta)
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}

export async function getPost(slug: string) {
  const file = fs
    .readdirSync(postsDir)
    .find((f) => f.replace(/\.mdx?$/, "") === slug);
  if (!file) throw new Error(`Post not found: ${slug}`);
  const { meta, content } = readPost(file);
  const processed = await remark().use(remarkGfm).use(html).process(content);
  return { meta, html: processed.toString() };
}
