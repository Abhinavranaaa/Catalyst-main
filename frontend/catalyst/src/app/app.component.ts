import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, provideRouter } from '@angular/router';
import { NavBarComponent } from "./nav-bar/nav-bar.component";
import { LandingPage } from './Pages/landing-page/landing-page.component';
import { ApplicationConfig } from '@angular/core';
import { HttpClientModule } from '@angular/common/http';
// This is the main application component that serves as the root of the Angular application.
// It sets up the router outlet and includes the navigation bar and landing page.
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, NavBarComponent, LandingPage , HttpClientModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'catalyst';
}
