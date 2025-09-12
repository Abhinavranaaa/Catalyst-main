import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RoadmapListComponent } from './roadmap-list.component';

describe('RoadmapListComponent', () => {
  let component: RoadmapListComponent;
  let fixture: ComponentFixture<RoadmapListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoadmapListComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(RoadmapListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
