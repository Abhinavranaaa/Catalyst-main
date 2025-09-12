import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RoadmapItem, Question } from './roadmap-item.interface';
import { DisplayManagerService } from '@services/display-manager/display-manager.service';

@Component({
  selector: 'app-roadmap-item',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './roadmap-item.component.html',
  styleUrls: ['./roadmap-item.component.scss']
})

export class RoadmapItemComponent {
  constructor(private displayManager: DisplayManagerService) {}

  @Input() roadmapItem!: RoadmapItem;
  @Output() saveToggle = new EventEmitter<string>();
  @Output() questionClick = new EventEmitter<{roadmapId: string, questionId: string}>();
  @Output() questionBookmark = new EventEmitter<{roadmapId: string, questionId: string}>();
  @Output() toggleExpansion = new EventEmitter<string>();

  onSaveToggle(): void {
    this.saveToggle.emit(this.roadmapItem.id);
  }

  onToggleExpansion(): void {
    this.toggleExpansion.emit(this.roadmapItem.id);
  }

  onQuestionClick(questionId: string): void {
    this.questionClick.emit({
      roadmapId: this.roadmapItem.id,
      questionId: questionId
    });
    this.displayManager.displayOverlay("question", questionId);
  }

  onQuestionBookmark(questionId: string): void {
    this.questionBookmark.emit({
      roadmapId: this.roadmapItem.id,
      questionId: questionId
    });
  }

  getDifficultyClass(difficulty: string): string {
    return `difficulty-${difficulty.toLowerCase()}`;
  }
}


