import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RoadmapCardComponent } from './roadmap-card.component';

describe('RoadmapCardComponent', () => {
  let component: RoadmapCardComponent;
  let fixture: ComponentFixture<RoadmapCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoadmapCardComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(RoadmapCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
