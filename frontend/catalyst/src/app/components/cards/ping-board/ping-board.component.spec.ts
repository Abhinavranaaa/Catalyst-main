import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PingBoardComponent } from './ping-board.component';

describe('PingBoardComponent', () => {
  let component: PingBoardComponent;
  let fixture: ComponentFixture<PingBoardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PingBoardComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(PingBoardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
