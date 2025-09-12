import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RoadmapPageComponent } from './roadmap-page.component';

describe('RoadmapPageComponent', () => {
  let component: RoadmapPageComponent;
  let fixture: ComponentFixture<RoadmapPageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoadmapPageComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(RoadmapPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
