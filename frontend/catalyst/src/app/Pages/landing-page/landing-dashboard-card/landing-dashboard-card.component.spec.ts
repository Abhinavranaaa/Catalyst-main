import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LandingDashboardCardComponent } from './landing-dashboard-card.component';

describe('LandingDashboardCardComponent', () => {
  let component: LandingDashboardCardComponent;
  let fixture: ComponentFixture<LandingDashboardCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandingDashboardCardComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(LandingDashboardCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
