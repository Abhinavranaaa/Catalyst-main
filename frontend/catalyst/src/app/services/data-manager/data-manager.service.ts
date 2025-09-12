import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, map } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class DataManagerService {
  /** internal data store */
  private data: Record<string, any> = {};

  /** subject to broadcast changes */
  private subject = new BehaviorSubject<Record<string, any>>(this.data);

  /** observable stream exposed to consumers */
  data$: Observable<Record<string, any>> = this.subject.asObservable();

  private loading: Record<string, boolean> = {};
  constructor() { }

  /** General load function (simulate API call for any key) */
  loadData<T>(key: string, loader: () => Promise<T> | T): void {
    if (this.loading[key]) return;
    this.loading[key] = true;

    Promise.resolve(loader()).then(value => {
      this.data[key] = value;
      this.subject.next({ ...this.data }); // emit updated store
      this.loading[key] = false;
    });
  }

   /**Get observable for a specific key */
  select<T>(key: string): Observable<T | null> {
    return this.data$.pipe(map(store => store[key] ?? null));
  }

  /** Get snapshot value immediately */
  snapshot<T>(key: string): T | null {
    return this.data[key] ?? null;
  }
}

