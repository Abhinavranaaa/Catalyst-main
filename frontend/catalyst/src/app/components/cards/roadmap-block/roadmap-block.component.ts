import { Input, Component, Output, EventEmitter } from '@angular/core';
import { FormGroup, FormControl } from '@angular/forms';
import { RouterModule } from '@angular/router';


@Component({
  selector: 'app-roadmap-block',
  standalone: true,
  imports: [RouterModule],
  templateUrl: './roadmap-block.component.html',
  styleUrl: './roadmap-block.component.scss'
})


export class RoadmapBlockComponent {
  isSaved = false;
  progressPercentage = 67; // 6/9 = ~67%

  onBlockClick(): void {
    // Handle block click - navigate to roadmap details
    console.log('Block clicked');
  }

  onSaveClick(event: Event): void {
    event.stopPropagation(); // Prevent block click when save button is clicked
    this.isSaved = !this.isSaved;
    console.log('Save clicked:', this.isSaved);
  }
}

