import { Component } from '@angular/core';

import { RoadmapListComponent } from "@pages/roadmap-page/roadmap-list/roadmap-list.component";
import { NavBarComponent } from "@app/nav-bar/nav-bar.component";

@Component({
  selector: 'app-roadmap-page',
  standalone: true,
  imports: [RoadmapListComponent, NavBarComponent],
  templateUrl: './roadmap-page.component.html',
  styleUrl: './roadmap-page.component.scss'
})
export class RoadmapPageComponent {

}
