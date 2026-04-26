#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DEFAULT_SITES = 'aiforge,craftdesk,deploystack,finstack,sellkit';
const GENERATED_MARKER = 'sbu-topic-hub-scaffold';

function parseArgs(argv) {
  const args = { sites: DEFAULT_SITES, dryRun: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || args.sites;
    else if (arg === '--dry-run') args.dryRun = true;
  }
  return args;
}

function pageTemplate() {
  return `/* ${GENERATED_MARKER} */
import { Metadata } from "next";
import Link from "next/link";
import { getAllPostsMeta } from "@/lib/posts";
import { siteConfig } from "@/config/site";
import styles from "./page.module.css";

function topicSlug(category: string) {
    return category.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function getTopicHubs() {
    const posts = getAllPostsMeta();
    const topics = new Map<string, { slug: string; category: string; posts: typeof posts }>();

    for (const post of posts) {
        const slug = topicSlug(post.category || "general");
        const existing = topics.get(slug);
        if (existing) existing.posts.push(post);
        else topics.set(slug, { slug, category: post.category || "General", posts: [post] });
    }

    return Array.from(topics.values()).sort((a, b) => b.posts.length - a.posts.length);
}

export const metadata: Metadata = {
    title: "Topic Hubs - Blog",
    description: "Browse focused article clusters by topic, workflow, and buyer intent.",
    alternates: {
        canonical: \`\${siteConfig.url}/blog/topics\`,
    },
    openGraph: {
        title: \`Topic Hubs - \${siteConfig.name}\`,
        description: "Focused article clusters for faster comparison, evaluation, and buying decisions.",
        url: \`\${siteConfig.url}/blog/topics\`,
    },
};

export const revalidate = 3600;

export default function BlogTopicsPage() {
    const hubs = getTopicHubs();
    const totalPosts = hubs.reduce((sum, hub) => sum + hub.posts.length, 0);

    return (
        <section className={styles.page}>
            <div className={styles.container}>
                <nav className={styles.breadcrumb} aria-label="Breadcrumb">
                    <Link href="/">Home</Link>
                    <span>/</span>
                    <Link href="/blog">Blog</Link>
                    <span>/</span>
                    <span>Topics</span>
                </nav>

                <header className={styles.header}>
                    <p className={styles.kicker}>Research map</p>
                    <h1 className={styles.title}>{siteConfig.name} Topic Hubs</h1>
                    <p className={styles.description}>
                        Move from broad research to focused article clusters by category,
                        workflow, and buying stage.
                    </p>
                    <div className={styles.stats}>
                        <div>
                            <strong>{totalPosts}</strong>
                            <span>articles</span>
                        </div>
                        <div>
                            <strong>{hubs.length}</strong>
                            <span>topic hubs</span>
                        </div>
                    </div>
                </header>

                <div className={styles.grid}>
                    {hubs.map((hub) => (
                        <article key={hub.slug} className={styles.hub}>
                            <div>
                                <h2>
                                    <Link href={\`/blog/topics/\${hub.slug}\`}>{hub.category}</Link>
                                </h2>
                                <p>
                                    {hub.posts.length} guides, comparisons, and operational notes for this topic.
                                </p>
                            </div>
                            <ul>
                                {hub.posts.slice(0, 3).map((post) => (
                                    <li key={post.slug}>
                                        <Link href={\`/blog/\${post.slug}\`}>{post.title}</Link>
                                    </li>
                                ))}
                            </ul>
                            <Link className={styles.link} href={\`/blog/topics/\${hub.slug}\`}>
                                Open hub
                            </Link>
                        </article>
                    ))}
                </div>
            </div>
        </section>
    );
}
`;
}

function clusterTemplate() {
  return `/* ${GENERATED_MARKER} */
import { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllPostsMeta } from "@/lib/posts";
import { siteConfig } from "@/config/site";
import PostCard from "@/components/PostCard";
import styles from "../page.module.css";

interface PageProps {
    params: Promise<{ cluster: string }>;
}

function topicSlug(category: string) {
    return category.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function getTopicHubs() {
    const posts = getAllPostsMeta();
    const topics = new Map<string, { slug: string; category: string; posts: typeof posts }>();

    for (const post of posts) {
        const slug = topicSlug(post.category || "general");
        const existing = topics.get(slug);
        if (existing) existing.posts.push(post);
        else topics.set(slug, { slug, category: post.category || "General", posts: [post] });
    }

    return Array.from(topics.values()).sort((a, b) => b.posts.length - a.posts.length);
}

export const revalidate = 3600;

export function generateStaticParams() {
    return getTopicHubs().map((hub) => ({ cluster: hub.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const { cluster } = await params;
    const hub = getTopicHubs().find((candidate) => candidate.slug === cluster);
    if (!hub) return { title: "Topic Hub Not Found" };

    return {
        title: \`\${hub.category} Topic Hub - \${siteConfig.name}\`,
        description: \`Browse \${siteConfig.name} articles for \${hub.category}: guides, comparisons, reviews, and buying decisions.\`,
        alternates: {
            canonical: \`\${siteConfig.url}/blog/topics/\${hub.slug}\`,
        },
        openGraph: {
            title: \`\${hub.category} Topic Hub - \${siteConfig.name}\`,
            description: \`Focused \${siteConfig.name} research for \${hub.category} decisions.\`,
            url: \`\${siteConfig.url}/blog/topics/\${hub.slug}\`,
        },
    };
}

export default async function BlogTopicClusterPage({ params }: PageProps) {
    const { cluster } = await params;
    const hubs = getTopicHubs();
    const hub = hubs.find((candidate) => candidate.slug === cluster);
    if (!hub) notFound();

    const relatedHubs = hubs.filter((candidate) => candidate.slug !== hub.slug).slice(0, 4);

    return (
        <section className={styles.page}>
            <div className={styles.container}>
                <nav className={styles.breadcrumb} aria-label="Breadcrumb">
                    <Link href="/">Home</Link>
                    <span>/</span>
                    <Link href="/blog">Blog</Link>
                    <span>/</span>
                    <Link href="/blog/topics">Topics</Link>
                    <span>/</span>
                    <span>{hub.category}</span>
                </nav>

                <header className={styles.header}>
                    <p className={styles.kicker}>Topic cluster</p>
                    <h1 className={styles.title}>{hub.category}</h1>
                    <p className={styles.description}>
                        {hub.posts.length} curated {siteConfig.name} articles for this topic, sorted by freshness.
                    </p>
                    <div className={styles.stats}>
                        <div>
                            <strong>{hub.posts.length}</strong>
                            <span>articles</span>
                        </div>
                        <div>
                            <strong>{relatedHubs.length}</strong>
                            <span>adjacent hubs</span>
                        </div>
                    </div>
                </header>

                <section className={styles.section}>
                    <h2>Decision Path</h2>
                    <p>
                        Start with the newest practical guide, then compare adjacent reviews,
                        pricing notes, and category alternatives before changing the operating stack.
                    </p>
                </section>

                <div className={styles.articleGrid}>
                    {hub.posts.map((post) => (
                        <PostCard key={post.slug} {...post} />
                    ))}
                </div>

                {relatedHubs.length > 0 && (
                    <section className={styles.section}>
                        <h2>Adjacent Hubs</h2>
                        <div className={styles.related}>
                            {relatedHubs.map((related) => (
                                <Link key={related.slug} href={\`/blog/topics/\${related.slug}\`}>
                                    {related.category}
                                    <span>{related.posts.length} articles</span>
                                </Link>
                            ))}
                        </div>
                    </section>
                )}
            </div>
        </section>
    );
}
`;
}

function cssTemplate() {
  return `/* ${GENERATED_MARKER} */
.page {
    padding: 2rem 0 4rem;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
}

.breadcrumb {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    font-size: 0.875rem;
    color: var(--text-secondary, #64748b);
    margin-bottom: 1.5rem;
}

.breadcrumb a {
    color: var(--text-secondary, #64748b);
    text-decoration: none;
}

.breadcrumb a:hover {
    color: var(--accent-color, #6366f1);
}

.header {
    max-width: 820px;
    margin-bottom: 2rem;
}

.kicker {
    margin: 0 0 0.5rem;
    font-size: 0.875rem;
    font-weight: 700;
    color: var(--accent-color, #6366f1);
}

.title {
    font-size: 2.25rem;
    line-height: 1.15;
    letter-spacing: 0;
    margin: 0 0 0.75rem;
    color: var(--text-primary, #0f172a);
}

.description {
    font-size: 1.0625rem;
    line-height: 1.65;
    color: var(--text-secondary, #64748b);
    margin: 0;
    overflow-wrap: anywhere;
}

.stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 160px));
    gap: 0.75rem;
    margin-top: 1.25rem;
}

.stats div {
    border: 1px solid var(--border-color, #e2e8f0);
    border-radius: 8px;
    padding: 1rem;
    background: var(--bg-secondary, #f8fafc);
}

.stats strong,
.stats span {
    display: block;
}

.stats strong {
    font-size: 1.5rem;
    color: var(--text-primary, #0f172a);
}

.stats span {
    margin-top: 0.25rem;
    font-size: 0.875rem;
    color: var(--text-secondary, #64748b);
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
}

.hub {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    border: 1px solid var(--border-color, #e2e8f0);
    border-radius: 8px;
    padding: 1.25rem;
    background: var(--bg-primary, #ffffff);
    min-width: 0;
}

.hub h2 {
    font-size: 1.125rem;
    line-height: 1.35;
    letter-spacing: 0;
    margin: 0 0 0.5rem;
}

.hub h2 a,
.hub li a,
.link {
    color: var(--text-primary, #0f172a);
    text-decoration: none;
}

.hub h2 a:hover,
.hub li a:hover,
.link:hover,
.related a:hover {
    color: var(--accent-color, #6366f1);
}

.hub p {
    margin: 0;
    color: var(--text-secondary, #64748b);
    line-height: 1.55;
}

.hub ul {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin: 0;
    padding-left: 1rem;
}

.hub li {
    color: var(--text-secondary, #64748b);
    line-height: 1.45;
    overflow-wrap: anywhere;
}

.link {
    width: fit-content;
    margin-top: auto;
    font-weight: 700;
}

.section {
    margin: 2rem 0;
    max-width: 820px;
}

.section h2 {
    font-size: 1.375rem;
    letter-spacing: 0;
    margin: 0 0 0.5rem;
    color: var(--text-primary, #0f172a);
}

.section p {
    margin: 0;
    color: var(--text-secondary, #64748b);
    line-height: 1.65;
}

.articleGrid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
}

.related {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.75rem;
}

.related a {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    border: 1px solid var(--border-color, #e2e8f0);
    border-radius: 8px;
    padding: 1rem;
    color: var(--text-primary, #0f172a);
    text-decoration: none;
}

.related span {
    color: var(--text-secondary, #64748b);
    font-size: 0.875rem;
}

@media (max-width: 640px) {
    .title {
        font-size: 1.75rem;
    }

    .stats {
        grid-template-columns: 1fr;
    }
}
`;
}

function ensureGeneratedFile(filePath, content, dryRun) {
  const exists = fs.existsSync(filePath);
  if (exists) {
    const current = fs.readFileSync(filePath, 'utf8');
    if (!current.includes(GENERATED_MARKER)) {
      throw new Error(`Refusing to overwrite non-generated file: ${filePath}`);
    }
    if (current === content) return 'unchanged';
  }

  if (!dryRun) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content, 'utf8');
  }
  return exists ? 'updated' : 'created';
}

function patchSitemap(siteId, dryRun) {
  const sitemapPath = path.join(ROOT, 'src', 'sbu', siteId, 'src', 'app', '(service)', 'sitemap.ts');
  let text = fs.readFileSync(sitemapPath, 'utf8');
  let changed = false;

  if (!text.includes('function topicSlug')) {
    const next = text.replace(
      /import \{ getAllCategories \} from "@\/lib\/categories";\r?\n/,
      (match) =>
        `${match}\nfunction topicSlug(category: string): string {\n    return category.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");\n}\n`,
    );
    if (next === text) throw new Error(`Unable to patch topicSlug helper: ${sitemapPath}`);
    text = next;
    changed = true;
  }

  if (!text.includes('const topicPages: MetadataRoute.Sitemap')) {
    text = text.replace(
      /    const postPages: MetadataRoute\.Sitemap = posts\.map\(\(post\) => \(\{\r?\n        url: `\$\{baseUrl\}\/blog\/\$\{post\.slug\}`,\r?\n        lastModified: new Date\(post\.date\),\r?\n        changeFrequency: "monthly" as const,\r?\n        priority: 0\.7,\r?\n    \}\)\);\r?\n/,
      (match) => `${match}\n    const topicSlugs = Array.from(new Set(posts.map((post) => topicSlug(post.category || "general"))));\n    const topicPages: MetadataRoute.Sitemap = [\n        {\n            url: \`${'${baseUrl}'}/blog\`,\n            lastModified: new Date(),\n            changeFrequency: "daily" as const,\n            priority: 0.9,\n        },\n        {\n            url: \`${'${baseUrl}'}/blog/topics\`,\n            lastModified: new Date(),\n            changeFrequency: "weekly" as const,\n            priority: 0.85,\n        },\n        ...topicSlugs.map((slug) => ({\n            url: \`${'${baseUrl}'}/blog/topics/${'${slug}'}\`,\n            lastModified: new Date(),\n            changeFrequency: "weekly" as const,\n            priority: 0.75,\n        })),\n    ];\n`,
    );
    changed = true;
  }

  if (!text.includes('...topicPages,')) {
    const next = text.replace(/        \.\.\.postPages,\r?\n/, (match) => `${match}        ...topicPages,\n`);
    if (next === text) throw new Error(`Unable to include topicPages in return: ${sitemapPath}`);
    text = next;
    changed = true;
  }

  if (changed && !dryRun) fs.writeFileSync(sitemapPath, text, 'utf8');
  return changed ? 'patched' : 'unchanged';
}

function scaffoldSite(siteId, dryRun) {
  const base = path.join(ROOT, 'src', 'sbu', siteId, 'src', 'app', '(service)', 'blog', 'topics');
  const files = [
    [path.join(base, 'page.tsx'), pageTemplate()],
    [path.join(base, '[cluster]', 'page.tsx'), clusterTemplate()],
    [path.join(base, 'page.module.css'), cssTemplate()],
  ];

  return {
    site: siteId,
    files: files.map(([file, content]) => ({
      file: path.relative(ROOT, file),
      status: ensureGeneratedFile(file, content, dryRun),
    })),
    sitemap: patchSitemap(siteId, dryRun),
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const sites = args.sites.split(',').map((site) => site.trim()).filter(Boolean);
  const results = sites.map((site) => scaffoldSite(site, args.dryRun));
  console.log(JSON.stringify({ dryRun: args.dryRun, results }, null, 2));
}

main();
