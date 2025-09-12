import { Input, Component, Output, EventEmitter } from '@angular/core';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { FormGroup, FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterModule , Router } from '@angular/router';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [RouterModule, ReactiveFormsModule, HttpClientModule],
  templateUrl: './login-page.component.html',
  styleUrl: './login-page.component.scss'
})
export class LoginPageComponent {
  private apiUrl = 'http://localhost:8000/api';

  signInForm = new FormGroup({
    email: new FormControl(''),
    password: new FormControl('')
  });

  signUpForm = new FormGroup({
    name: new FormControl(''),
    email: new FormControl(''),
    password: new FormControl('')
  });

  constructor(private http: HttpClient, private router: Router) {}

  ngAfterViewInit() {
    const signUpButton = document.getElementById('signUp');
    const signInButton = document.getElementById('signIn');
    const container = document.getElementById('container');

    if (signUpButton && container) {
      signUpButton.addEventListener('click', () => {
        container.classList.add("right-panel-active");
      });
    }

    if (signInButton && container) {
      signInButton.addEventListener('click', () => {
        container.classList.remove("right-panel-active");
      });
    }
  }
  onSignIn() {
    console.log('SignIn Payload:', this.signInForm.value);
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
    });

    this.http.post(`https://django-web-109334363006.us-central1.run.app/api/login`, this.signInForm.value , {
      headers,
      withCredentials : true
    }).subscribe({
      next: (response: any) => {
        // Store JWT token
        localStorage.setItem('jwt', response.jwt);
        alert('Login successful: You are being redirected to the home page');
        this.router.navigate(['/prompt']);
      },
      error: (error) => {
        console.error('Login failed:', error);
        alert('Login failed: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }

  onSignUp() {
    console.log('SignUp Payload:', this.signUpForm.value);
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
    });

    this.http.post(`https://django-web-109334363006.us-central1.run.app/api/register`, this.signUpForm.value, {
      headers,
      withCredentials: true
    }).subscribe({
      next: () => {
        alert('Registration successful! Please sign in');
        const container = document.getElementById('container');
        if (container) container.classList.remove("right-panel-active");
      },
      error: (error) => {
        console.error('Registration failed:', error);
        alert('Registration failed: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }

}

