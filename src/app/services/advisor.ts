import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PromptRequest, PromptResponse } from '../models/advisor.models';

@Injectable({
  providedIn: 'root'
})
export class AdvisorService {
  private http = inject(HttpClient);
  private apiUrl = 'http://127.0.0.1:8000';

  sendPrompt(payload: PromptRequest): Observable<PromptResponse> {
    return this.http.post<PromptResponse>(`${this.apiUrl}/advisor/prompt`, payload);
  }

  health(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }
}