import { Component, Input } from '@angular/core';
import { NgFor } from '@angular/common';

@Component({
  selector: 'app-box-options',
  standalone: true,
  imports: [NgFor],
  templateUrl: './box-options.component.html',
  styleUrl: './box-options.component.scss'
})
export class BoxOptionsComponent {

  @Input() options: { label: string }[];
  @Input() title: string = 'Options';

  constructor() {
    this.options = [{ 'label': 'Option 1' }, { 'label': 'Option 2' }, { 'label': 'Option 3' }];
    if (!this.title) {
      this.title = 'Options';
    }
  }
  ngOnInit(): void {

  }
  selectOption(option: Object) {
    console.log(`Selected option: ${option}`);
  }
}
