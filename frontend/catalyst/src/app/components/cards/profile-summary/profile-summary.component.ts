import { Component } from '@angular/core';
import {ScoreCardComponent} from "@components/cards/profile-summary/score-card/score-card.component";

@Component({
  selector: 'app-profile-summary',
  standalone: true,
  imports: [ScoreCardComponent],
  templateUrl: './profile-summary.component.html',
  styleUrl: './profile-summary.component.scss'
})
export class ProfileSummaryComponent {

}
