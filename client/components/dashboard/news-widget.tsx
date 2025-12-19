"use client";

import { GlassCard, GlassCardHeader, GlassCardTitle } from "@/components/shared/glass-card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Newspaper, Clock, ExternalLink } from "lucide-react";
import { newsArticles } from "@/mocks/mock-data";
import { formatRelativeTime, cn } from "@/lib/utils";

/**
 * NewsWidget - Tech news feed widget
 *
 * Displays aggregated tech news from multiple sources.
 * Categories: AWS, Azure, GCP, AI/ML
 */

const categoryColors: Record<string, string> = {
  "cloud-aws": "bg-orange-500/20 text-orange-400",
  "cloud-azure": "bg-blue-500/20 text-blue-400",
  "cloud-gcp": "bg-red-500/20 text-red-400",
  ai: "bg-purple-500/20 text-purple-400",
};

const sourceIcons: Record<string, string> = {
  aws: "🟠",
  google: "🔵",
  azure: "🔷",
  techcrunch: "🟢",
};

export function NewsWidget() {
  return (
    <GlassCard className="h-full flex flex-col">
      <GlassCardHeader>
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-magenta-light" />
          <GlassCardTitle>Notícias Tech</GlassCardTitle>
        </div>
        <Badge variant="outline" className="text-xs">
          {newsArticles.length} novidades
        </Badge>
      </GlassCardHeader>

      <ScrollArea className="flex-1 -mx-4 px-4">
        <div className="space-y-3">
          {newsArticles.map((article) => (
            <NewsCard key={article.id} article={article} />
          ))}
        </div>
      </ScrollArea>
    </GlassCard>
  );
}

interface NewsCardProps {
  article: (typeof newsArticles)[0];
}

function NewsCard({ article }: NewsCardProps) {
  const timeAgo = formatRelativeTime(article.publishedAt);
  const categoryColor = categoryColors[article.category] || "bg-gray-500/20 text-gray-400";
  const sourceIcon = sourceIcons[article.sourceIcon] || "📰";

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "block p-3 rounded-lg",
        "border border-border",
        "transition-all duration-150",
        "hover:bg-white/5 hover:border-magenta-mid/30",
        "group"
      )}
    >
      {/* Source & Category */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm">{sourceIcon}</span>
        <span className="text-xs text-text-muted">{article.source}</span>
        <Badge className={cn("ml-auto text-[10px]", categoryColor)}>
          {article.category === "ai" ? "AI" : article.category.split("-")[1]?.toUpperCase()}
        </Badge>
      </div>

      {/* Title */}
      <h4 className="text-sm font-medium text-text-primary mb-2 line-clamp-2 group-hover:text-blue-light transition-colors">
        {article.title}
      </h4>

      {/* Summary */}
      <p className="text-xs text-text-muted line-clamp-2 mb-2">
        {article.summary}
      </p>

      {/* Footer */}
      <div className="flex items-center gap-4 text-xs text-text-muted">
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>{timeAgo}</span>
        </div>
        <div className="flex items-center gap-1">
          <span>{article.readTime} min de leitura</span>
        </div>
        <ExternalLink className="w-3 h-3 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </a>
  );
}

export default NewsWidget;
