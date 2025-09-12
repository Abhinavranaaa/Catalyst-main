import { TestBed } from '@angular/core/testing';

import { DisplayManagerService } from './display-manager.service';

describe('DisplayManagerService', () => {
  let service: DisplayManagerService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(DisplayManagerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
