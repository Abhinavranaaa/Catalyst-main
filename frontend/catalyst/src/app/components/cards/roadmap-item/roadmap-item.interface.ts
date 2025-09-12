export interface RoadmapItem {
  id: string;
  title: string;
  summary: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  progressPercentage: number;
  isSaved: boolean;
  questions: Question[];
  isExpanded?: boolean;
}

export interface Question {
  id: string;
  title: string;
  summary: string;
  isBookmarked: boolean;
  difficulty: 'Easy' | 'Medium' | 'Hard';
}


