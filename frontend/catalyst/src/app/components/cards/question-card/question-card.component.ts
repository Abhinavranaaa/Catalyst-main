import { Input, Component, Output, EventEmitter, input } from '@angular/core';
import { FormGroup, FormControl } from '@angular/forms';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-question-card',
  standalone: true,
  imports: [RouterModule],
  templateUrl: './question-card.component.html',
  styleUrl: './question-card.component.scss'
})
export class QuestionCardComponent {
  
  @Input() question: any;

  ngAfterViewInit() {
    const floating_btn = document.querySelector('.floating-btn');
    const close_btn = document.querySelector('.close-btn');
    const social_panel_container = document.querySelector('.social-panel-container');

    if (floating_btn && social_panel_container) {
      floating_btn.addEventListener('click', () => {
        social_panel_container.classList.toggle('visible');
      });
    }

    if (close_btn && social_panel_container) {
      close_btn.addEventListener('click', () => {
        social_panel_container.classList.remove('visible');
      });
    }
  }
}

