import { Injectable, ApplicationRef, ComponentRef, EnvironmentInjector, createComponent } from '@angular/core';
import { QuestionCardComponent } from '@app/components/cards/question-card/question-card.component';
import { Question } from '@components/cards/roadmap-item/roadmap-item.interface';

@Injectable({
  providedIn: 'root'
})
export class DisplayManagerService {

  constructor(
    private appRef: ApplicationRef,
    private env: EnvironmentInjector
  ) { }
  displayOverlay(type?: string, id?: string): void {
    // Logic to display an overlay based on the type and id
    let overlay = document.getElementById('overlay');
    if (overlay) {
      overlay.style.display = 'block';
    } else {
      const newOverlay = document.createElement('div');
      newOverlay.id = 'overlay';
      document.body.appendChild(newOverlay);
      overlay = document.getElementById('overlay');
      if (!overlay) {
        console.error('Overlay element could not be created');
        return;
      }
      overlay.style.display = 'block';
    }

 

    let refView : ComponentRef<any> | null = null;
    if (type) {
      refView = this.createView(type, id);
    }

    overlay?.addEventListener('click', () => {
      overlay.style.display = 'none';
      if (refView) {
        this.appRef.detachView(refView.hostView);
        refView.destroy();
      }
    });
  }

  private createView(type: string, id?: string): ComponentRef<any> {
    // 1. Create the component instance
    const compRef: ComponentRef<QuestionCardComponent> =
      createComponent(QuestionCardComponent, { environmentInjector: this.env });

    // 3. Add to DOM manually
    document.body.appendChild((compRef.hostView as any).rootNodes[0]);
    return compRef;
  }
}
