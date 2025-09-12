import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, catchError, of } from 'rxjs';
import { RoadmapItem, Question } from "@components/cards/roadmap-item/roadmap-item.interface";

@Injectable({
  providedIn: 'root'
})
export class RoadmapService {
  private roadmapItemsSubject = new BehaviorSubject<RoadmapItem[]>([]);
  roadmapItems$: Observable<RoadmapItem[]> = this.roadmapItemsSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadDataFromJson();
  }

  private loadDataFromJson(): void {
    this.http.get<any>('/assets/data/example.json')
      .pipe(
        catchError(error => {
          console.error('Error loading roadmap data from JSON:', error);
          return of({ data: { roadmapItems: this.getFallbackData() } });
        })
      )
      .subscribe(data => {
        const roadmapItems = data.data?.roadmapItems || this.getFallbackData();
        this.roadmapItemsSubject.next(roadmapItems);
      });
  }

  private getFallbackData(): RoadmapItem[] {
    // Fallback data in case JSON loading fails
    return [
      {
        id: 'fallback-1',
        title: 'Fallback Topic',
        summary: 'This is fallback data loaded when JSON import fails. Please check your example.json file.',
        difficulty: 'Easy',
        progressPercentage: 0,
        isSaved: false,
        isExpanded: false,
        questions: [
          {
            id: 'fallback-q1',
            title: 'Sample Question',
            summary: 'This is a sample question from fallback data.',
            isBookmarked: false,
            difficulty: 'Easy'
          }
        ]
      }
    ];
  }

  // Method to reload data from JSON (useful for refreshing data)
  reloadData(): void {
    this.loadDataFromJson();
  }

  getRoadmapItems(): RoadmapItem[] {
    return this.roadmapItemsSubject.value;
  }

  updateRoadmapItem(updatedItem: RoadmapItem): void {
    const currentItems = this.roadmapItemsSubject.value;
    const updatedItems = currentItems.map(item =>
      item.id === updatedItem.id ? updatedItem : item
    );
    this.roadmapItemsSubject.next(updatedItems);
  }

  toggleSaveStatus(itemId: string): void {
    const currentItems = this.roadmapItemsSubject.value;
    const updatedItems = currentItems.map(item =>
      item.id === itemId ? { ...item, isSaved: !item.isSaved } : item
    );
    this.roadmapItemsSubject.next(updatedItems);
  }

  toggleExpansion(itemId: string): void {
    const currentItems = this.roadmapItemsSubject.value;
    const updatedItems = currentItems.map(item =>
      item.id === itemId ? { ...item, isExpanded: !item.isExpanded } : item
    );
    this.roadmapItemsSubject.next(updatedItems);
  }

  toggleQuestionBookmark(roadmapId: string, questionId: string): void {
    const currentItems = this.roadmapItemsSubject.value;
    const updatedItems = currentItems.map(item => {
      if (item.id === roadmapId) {
        const updatedQuestions = item.questions.map(question =>
          question.id === questionId
            ? { ...question, isBookmarked: !question.isBookmarked }
            : question
        );
        return { ...item, questions: updatedQuestions };
      }
      return item;
    });
    this.roadmapItemsSubject.next(updatedItems);
  }

  updateProgress(itemId: string, progressPercentage: number): void {
    const currentItems = this.roadmapItemsSubject.value;
    const updatedItems = currentItems.map(item =>
      item.id === itemId ? { ...item, progressPercentage } : item
    );
    this.roadmapItemsSubject.next(updatedItems);
  }

  addRoadmapItem(newItem: RoadmapItem): void {
    const currentItems = this.roadmapItemsSubject.value;
    this.roadmapItemsSubject.next([...currentItems, newItem]);
  }

  removeRoadmapItem(itemId: string): void {
    const currentItems = this.roadmapItemsSubject.value;
    const filteredItems = currentItems.filter(item => item.id !== itemId);
    this.roadmapItemsSubject.next(filteredItems);
  }

  addQuestion(roadmapId: string, newQuestion: Question): void {
    const currentItems = this.roadmapItemsSubject.value;
    const updatedItems = currentItems.map(item => {
      if (item.id === roadmapId) {
        return { ...item, questions: [...item.questions, newQuestion] };
      }
      return item;
    });
    this.roadmapItemsSubject.next(updatedItems);
  }

  removeQuestion(roadmapId: string, questionId: string): void {
    const currentItems = this.roadmapItemsSubject.value;
    const updatedItems = currentItems.map(item => {
      if (item.id === roadmapId) {
        const updatedQuestions = item.questions.filter(q => q.id !== questionId);
        return { ...item, questions: updatedQuestions };
      }
      return item;
    });
    this.roadmapItemsSubject.next(updatedItems);
  }
}
