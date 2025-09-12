import { Component, Input } from '@angular/core';

@Component({
  selector: 'nav-button',
  standalone: true,
  imports: [],
  templateUrl: './nav-button.component.html',
  styleUrl: './nav-button.component.scss'
})
export class NavButton {

  @Input() key: string = '';
  @Input() value: string = '';
}
