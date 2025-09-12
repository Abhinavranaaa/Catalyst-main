import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-roadmaps-scroll',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './roadmaps-scroll.component.html',
  styleUrl: './roadmaps-scroll.component.scss'
})
export class RoadmapsScrollComponent {
  roadmaps = ['Aryan', 'Vohra', 'John', 'Doe', 'Jane', 'Bob', 'Brown'];

  constructor() {
    // Initialization logic can go here
  }
}
