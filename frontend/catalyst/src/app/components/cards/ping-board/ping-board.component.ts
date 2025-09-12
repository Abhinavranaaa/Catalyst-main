import { Component } from '@angular/core';
import {NotificationComponent} from "@components/cards/ping-board/notification/notification.component";

@Component({
  selector: 'app-ping-board',
  standalone: true,
  imports: [
    NotificationComponent
  ],
  templateUrl: './ping-board.component.html',
  styleUrl: './ping-board.component.scss'
})
export class PingBoardComponent {

}
