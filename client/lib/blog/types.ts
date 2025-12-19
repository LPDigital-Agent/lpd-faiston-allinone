/**
 * Blog Types - Faiston One Internal Blog
 *
 * Type definitions for the corporate blog system.
 * Articles are imported from faiston.com/blogs/ and reformatted
 * to match the Faiston One design system.
 */

/**
 * Blog category types with semantic meaning.
 * Each category maps to a specific color in the design system.
 */
export type BlogCategory =
  | "seguranca"      // Red - Security & Cybersecurity
  | "infraestrutura" // Blue - Infrastructure & Networks
  | "cloud"          // Cyan - Cloud Computing
  | "inovacao"       // Magenta - Innovation & Technology
  | "blog-news";     // Green - General Blog & News

/**
 * Blog post structure for display in cards and listings.
 */
export interface BlogPost {
  /** Unique identifier */
  id: string;

  /** URL-friendly slug for routing */
  slug: string;

  /** Article title */
  title: string;

  /** Short description for cards (150-200 chars) */
  excerpt: string;

  /** Full article content in markdown/HTML */
  content: string;

  /** Article category for filtering and badge colors */
  category: BlogCategory;

  /** Human-readable category label in Portuguese */
  categoryLabel: string;

  /** Publication date in ISO format (YYYY-MM-DD) */
  publishedAt: string;

  /** Estimated reading time in minutes */
  readTime: number;

  /** Whether this is a featured/highlighted article */
  featured: boolean;

  /** Original URL on faiston.com (optional) */
  externalUrl?: string;

  /** Author name (optional) */
  author?: string;

  /** Cover image URL (optional) */
  coverImage?: string;

  /** SEO keywords (optional) */
  tags?: string[];
}

/**
 * Category configuration for UI rendering.
 * Maps category slugs to display properties.
 */
export interface CategoryConfig {
  /** Category slug */
  slug: BlogCategory;

  /** Display label in Portuguese */
  label: string;

  /** Tailwind CSS classes for badge background */
  bgClass: string;

  /** Tailwind CSS classes for badge text */
  textClass: string;

  /** Tailwind CSS classes for border */
  borderClass: string;
}

/**
 * Category configurations with Faiston design system colors.
 */
export const CATEGORY_CONFIG: Record<BlogCategory, CategoryConfig> = {
  seguranca: {
    slug: "seguranca",
    label: "Seguranca",
    bgClass: "bg-red-500/20",
    textClass: "text-red-400",
    borderClass: "border-red-500/30",
  },
  infraestrutura: {
    slug: "infraestrutura",
    label: "Infraestrutura",
    bgClass: "bg-blue-500/20",
    textClass: "text-blue-light",
    borderClass: "border-blue-500/30",
  },
  cloud: {
    slug: "cloud",
    label: "Cloud",
    bgClass: "bg-cyan-500/20",
    textClass: "text-cyan-400",
    borderClass: "border-cyan-500/30",
  },
  inovacao: {
    slug: "inovacao",
    label: "Inovacao",
    bgClass: "bg-magenta-500/20",
    textClass: "text-magenta-light",
    borderClass: "border-magenta-500/30",
  },
  "blog-news": {
    slug: "blog-news",
    label: "Blog & News",
    bgClass: "bg-green-500/20",
    textClass: "text-green-400",
    borderClass: "border-green-500/30",
  },
};

/**
 * Get category configuration by slug.
 */
export function getCategoryConfig(category: BlogCategory): CategoryConfig {
  return CATEGORY_CONFIG[category];
}

/**
 * Format date for display in Portuguese.
 */
export function formatBlogDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
