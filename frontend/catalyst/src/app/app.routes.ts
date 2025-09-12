import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginPageComponent } from './components/cards/login-card/login-page.component';
import { QuestionCardComponent } from './components/cards/question-card/question-card.component';
import { UserProfileComponent } from './Pages/user-profile/user-profile.component';
import { LandingPage } from '@pages/landing-page/landing-page.component';
import { PromptPageComponent } from '@pages/prompt-page/prompt-page.component';
import { StudyPlanComponent } from "@pages/study-plan/study-plan.component";
import { RoadmapListComponent } from "@app/Pages/roadmap-page/roadmap-list/roadmap-list.component";
import { RoadmapPageComponent } from "@pages/roadmap-page/roadmap-page.component";
import {RoadmapBlockComponent} from "@components/cards/roadmap-block/roadmap-block.component";
import {ScoreCardComponent} from "@components/cards/profile-summary/score-card/score-card.component";
import {ProfileSummaryComponent} from "@components/cards/profile-summary/profile-summary.component";
import {PingBoardComponent} from "@components/cards/ping-board/ping-board.component";


export const routes: Routes = [
    { path: '', redirectTo: '/home', pathMatch: 'full' },
    { path: 'home', component: LandingPage },
    { path: 'prompt', component: PromptPageComponent },
    { path: 'questionCard', component: QuestionCardComponent },
    { path: 'userHome', component: UserProfileComponent },
    { path: 'plan', component: StudyPlanComponent },
    { path: 'roadmap', component: RoadmapPageComponent },
    {path: 'preview' , component: PingBoardComponent},
  //  { path: 'roadmap', component: RoadmapListComponent }

];
