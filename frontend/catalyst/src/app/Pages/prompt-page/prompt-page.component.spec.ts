import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PromptPageComponent } from './prompt-page.component';

describe('PromptPageComponent', () => {
  let component: PromptPageComponent;
  let fixture: ComponentFixture<PromptPageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PromptPageComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(PromptPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
