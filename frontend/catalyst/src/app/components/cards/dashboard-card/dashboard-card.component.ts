import { Component, input, Input } from '@angular/core';
import { NgClass, NgIf } from '@angular/common';

@Component({
  selector: 'dashboard-card',
  standalone: true,
  imports: [NgClass, NgIf],
  templateUrl: './dashboard-card.component.html',
  styleUrl: './dashboard-card.component.scss'
})
export class DashboardCardComponent {
  color = input("bg-primary");
  title = input("");
  @Input() content: string = "";
  backgroundColor = input("");

  displayImg = false;
  ngOnInit() {
    if (this.content.indexOf(".png") !== -1) {
      this.displayImg = true;
    }
  }
}
