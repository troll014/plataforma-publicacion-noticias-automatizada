import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Image from "next/image";

interface NewsCardProps {
  title: string;
  imageUrl: string;
  summary: string;
  publicationDate: string;
  source: string;
}

export default function NewsCard({
  title,
  imageUrl,
  summary,
  publicationDate,
  source,
}: NewsCardProps) {
  return (
    <Card className="overflow-hidden transition-all duration-300 hover:scale-[1.02] bg-white/10 backdrop-blur-lg border-white/20">
      <div className="relative h-48 w-full">
        <Image
          src={imageUrl}
          alt={title}
          fill
          className="object-cover"
          priority
        />
      </div>
      <CardHeader className="text-white">
        <h3 className="text-xl font-bold line-clamp-2">{title}</h3>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-gray-300 line-clamp-3">{summary}</p>
        <div className="flex justify-between items-center">
          <Badge variant="secondary" className="bg-white/20 text-white hover:bg-white/30">
            {source}
          </Badge>
          <span className="text-sm text-gray-400">
            {new Date(publicationDate).toLocaleDateString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
