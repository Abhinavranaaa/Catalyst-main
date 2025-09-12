import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject, takeUntil } from 'rxjs';
import { RoadmapItem } from "@components/cards/roadmap-item/roadmap-item.interface";
import { RoadmapService } from './roadmap.service';
import { RoadmapItemComponent } from "@components/cards/roadmap-item/roadmap-item.component";

@Component({
  selector: 'app-roadmap-list',
  standalone: true,
  imports: [CommonModule, RoadmapItemComponent],
  template: `
    <div class="container">
      <div class="left-panel">
        <h2>Roadmap Progress</h2>
        <p>Track your progress through data structures and algorithms. Click on any topic to explore questions and practice problems.</p>
      </div>

      <div class="right-panel">
        <div class="roadmap-grid">
          <app-roadmap-item
            *ngFor="let item of roadmapItems"
            [roadmapItem]="item"
            (saveToggle)="onSaveToggle($event)"
            (questionClick)="onQuestionClick($event)"
            (questionBookmark)="onQuestionBookmark($event)"
            (toggleExpansion)="onToggleExpansion($event)">
          </app-roadmap-item>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./roadmap-list.component.scss']
})
export class RoadmapListComponent implements OnInit, OnDestroy {
  roadmapItems: RoadmapItem[] = [];
  private destroy$ = new Subject<void>();

  constructor(private roadmapService: RoadmapService) {}

  ngOnInit(): void {
    this.roadmapService.roadmapItems$
      .pipe(takeUntil(this.destroy$))
      .subscribe(items => {
        this.roadmapItems = items;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onSaveToggle(itemId: string): void {
    this.roadmapService.toggleSaveStatus(itemId);
  }

  onQuestionClick(event: {roadmapId: string, questionId: string}): void {
    console.log('Question clicked:', event);
    // Handle question click - navigate to question detail, etc.
  }

  onQuestionBookmark(event: {roadmapId: string, questionId: string}): void {
    this.roadmapService.toggleQuestionBookmark(event.roadmapId, event.questionId);
  }

  onToggleExpansion(itemId: string): void {
    this.roadmapService.toggleExpansion(itemId);
  }
}
