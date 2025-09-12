import { Component } from '@angular/core';
import {NavBarComponent} from "@app/nav-bar/nav-bar.component";

@Component({
  selector: 'app-study-plan',
  standalone: true,
  imports: [
    NavBarComponent
  ],
  templateUrl: './study-plan.component.html',
  styleUrl: './study-plan.component.scss'
})
export class StudyPlanComponent {

}
