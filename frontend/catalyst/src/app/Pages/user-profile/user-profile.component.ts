import { Component } from '@angular/core';
import { DashboardCardComponent } from '@app/components/cards/dashboard-card/dashboard-card.component';
import { NavButton } from './nav-button/nav-button.component';
import { RoadmapsScrollComponent } from "./roadmaps-scroll/roadmaps-scroll.component";
import { DataManagerService } from '@services/data-manager/data-manager.service';

export interface UserProfile {
  name: string;
  email: string;
  bio: string;
}

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [DashboardCardComponent, NavButton, RoadmapsScrollComponent],
  templateUrl: './user-profile.component.html',
  styleUrls: ['./user-profile.component.scss']
})
export class UserProfileComponent {
  user = {
    name: 'John Doe',
    email: 'john.doe@example.com',
    bio: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.'
  };
  constructor(private dataService: DataManagerService) {}


}
