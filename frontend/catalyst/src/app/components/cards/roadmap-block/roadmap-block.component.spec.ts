import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RoadmapBlockComponent } from './roadmap-block.component';

describe('RoadmapBlockComponent', () => {
  let component: RoadmapBlockComponent;
  let fixture: ComponentFixture<RoadmapBlockComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoadmapBlockComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(RoadmapBlockComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
