import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RoadmapsScrollComponent } from './roadmaps-scroll.component';

describe('RoadmapsScrollComponent', () => {
  let component: RoadmapsScrollComponent;
  let fixture: ComponentFixture<RoadmapsScrollComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoadmapsScrollComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(RoadmapsScrollComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
