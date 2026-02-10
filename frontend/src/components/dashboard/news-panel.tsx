"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTickerNews } from "@/hooks/use-api";
import type { NewsArticle } from "@/lib/types";

interface NewsPanelProps {
  ticker: string | null;
}

export function NewsPanel({ ticker }: NewsPanelProps) {
  const { data: articles, loading } = useTickerNews(ticker);

  if (!ticker) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <div className="text-zinc-500">Select a ticker to view news</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{ticker} News</CardTitle>
      </CardHeader>
      <CardContent>
        {loading && <div className="text-zinc-500 text-sm">Loading news...</div>}
        {!loading && articles.length === 0 && (
          <div className="text-zinc-500 text-sm text-center py-4">
            No news available. Configure Finnhub/Benzinga API keys to enable.
          </div>
        )}
        <div className="space-y-2 max-h-96 overflow-auto">
          {articles.map((article, i) => (
            <ArticleRow key={i} article={article} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ArticleRow({ article }: { article: NewsArticle }) {
  const sentimentVariant = article.sentiment === "positive" ? "buy" as const
    : article.sentiment === "negative" ? "sell" as const
    : "neutral" as const;

  return (
    <div className="rounded-lg bg-zinc-900 p-3 space-y-1">
      <div className="flex items-start justify-between gap-2">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-zinc-200 hover:text-white transition-colors leading-tight"
        >
          {article.headline}
        </a>
        <Badge variant={sentimentVariant}>
          {article.sentiment}
        </Badge>
      </div>
      <div className="flex items-center gap-3 text-xs text-zinc-500">
        <span>{article.source}</span>
        <span>{new Date(article.published_at).toLocaleDateString()}</span>
      </div>
      {article.summary && (
        <p className="text-xs text-zinc-400 mt-1">{article.summary}</p>
      )}
    </div>
  );
}
