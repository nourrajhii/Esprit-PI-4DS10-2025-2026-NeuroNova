import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdvisorService } from '../../services/advisor';
import {
  ChatMessage,
  PromptResponse,
  PropertyItem
} from '../../models/advisor.models';

@Component({
  selector: 'app-prompt-advisor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './prompt-advisor.html',
  styleUrl: './prompt-advisor.css'
})
export class PromptAdvisorComponent {
  private advisorService = inject(AdvisorService);

  userPrompt = '';
  loading = false;
  errorMessage = '';

  messages: ChatMessage[] = [];
  lastResponse: PromptResponse | null = null;
  properties: PropertyItem[] = [];

  quickPrompts: string[] = [
    'Je cherche un appartement à louer à Bizerte avec 2 chambres et un budget de 1200 DT',
    'Je veux une villa à vendre à Nabeul avec un budget de 450000 DT',
    'Je cherche un studio à louer à Tunis',
    'Je veux un terrain à vendre à Sousse'
  ];

  sendMessage(): void {
    const prompt = this.userPrompt.trim();

    if (!prompt || this.loading) {
      return;
    }

    this.errorMessage = '';

    this.messages.push({
      role: 'user',
      content: prompt
    });

    const conversationHistory = [...this.messages];

    this.userPrompt = '';
    this.loading = true;

    this.advisorService.sendPrompt({
      prompt,
      conversation_history: conversationHistory
    }).subscribe({
      next: (res: PromptResponse) => {
        this.lastResponse = res;
        this.properties = this.sortProperties(res.properties || []);

        this.messages.push({
          role: 'assistant',
          content: this.buildAssistantMessage(res)
        });

        this.loading = false;
      },
      error: (err) => {
        this.errorMessage =
          err?.error?.detail ||
          'Une erreur est survenue lors de la communication avec le serveur.';
        this.loading = false;
      }
    });
  }

  useQuickPrompt(prompt: string): void {
    this.userPrompt = prompt;
  }

  private buildAssistantMessage(res: PromptResponse): string {
    if (!res.is_real_estate_query) {
      return res.natural_response || 'Votre demande ne semble pas liée à l’immobilier.';
    }

    const parts: string[] = [];

    if (res.natural_response?.trim()) {
      parts.push(res.natural_response.trim());
    }

    if (res.advice?.trim()) {
      parts.push(res.advice.trim());
    }

    return parts.join('\n\n');
  }

  private sortProperties(properties: PropertyItem[]): PropertyItem[] {
    return [...properties].sort((a, b) => {
      const scoreA = a.score ?? -999999;
      const scoreB = b.score ?? -999999;

      if (scoreB !== scoreA) {
        return scoreB - scoreA;
      }

      const priceA = a.price ?? Number.MAX_SAFE_INTEGER;
      const priceB = b.price ?? Number.MAX_SAFE_INTEGER;
      return priceA - priceB;
    });
  }

  getTopProperty(): PropertyItem | null {
    return this.properties.length ? this.properties[0] : null;
  }

  getOtherProperties(): PropertyItem[] {
    return this.properties.length > 1 ? this.properties.slice(1) : [];
  }

  getShortAdvice(): string {
    if (!this.lastResponse?.advice?.trim()) {
      return 'Comparez l’emplacement, la surface, l’état du bien et le prix au m² avant de prendre votre décision.';
    }
    return this.lastResponse.advice;
  }

  getTransactionLabel(): string {
    const value = this.lastResponse?.criteria?.transaction_type;
    return value || 'Non précisé';
  }

  getCategoryLabel(): string {
    const value = this.lastResponse?.criteria?.category;
    if (!value) return 'Non précisée';
    if (value === 'residential') return 'Résidentiel';
    if (value === 'commercial') return 'Commercial';
    if (value === 'land') return 'Terrain';
    return String(value);
  }

  getCityLabel(): string {
    const value = this.lastResponse?.criteria?.city;
    return value || 'Non précisée';
  }

  getBudgetMinLabel(): string {
    return this.formatPrice(this.lastResponse?.criteria?.min_price ?? null);
  }

  getBudgetMaxLabel(): string {
    return this.formatPrice(this.lastResponse?.criteria?.max_price ?? null);
  }

  getRoomsCriteriaLabel(): string {
    const value = this.lastResponse?.criteria?.rooms;
    return value === null || value === undefined ? '-' : `${value}`;
  }

  formatPrice(value: number | null | undefined): string {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('fr-FR', {
      maximumFractionDigits: 0
    }).format(value) + ' DT';
  }

  formatSurface(value: number | null | undefined): string {
    if (value === null || value === undefined) return '-';
    return `${value} m²`;
  }

  formatRooms(value: number | null | undefined): string {
    if (value === null || value === undefined || value <= 0) return '-';
    return value === 1 ? '1 pièce' : `${value} pièces`;
  }

  formatBathrooms(value: number | null | undefined): string {
    if (value === null || value === undefined || value <= 0) return '-';
    return value === 1 ? '1 SDB' : `${value} SDB`;
  }

  getPropertyLocation(property: PropertyItem): string {
    const city = property.city || '';
    const region = property.region || '';

    if (city && region && city !== region) {
      return `${city} - ${region}`;
    }

    return city || region || 'Localisation non précisée';
  }

  getPropertyTypeLabel(property: PropertyItem): string {
    const raw =
      property.detected_sub_type ||
      property.property_type ||
      property.category ||
      'bien immobilier';

    const value = String(raw).toLowerCase();

    if (value.includes('appartement')) return 'Appartement';
    if (value.includes('studio')) return 'Studio';
    if (value.includes('villa')) return 'Villa';
    if (value.includes('maison')) return 'Maison';
    if (value.includes('terrain')) return 'Terrain';
    if (value.includes('local')) return 'Local commercial';
    if (value.includes('bureau')) return 'Bureau';
    if (value.includes('commercial')) return 'Commercial';

    return String(raw);
  }

  getPropertyIcon(property: PropertyItem): string {
    const value = this.getPropertyTypeLabel(property).toLowerCase();

    if (value.includes('appartement')) return '🏢';
    if (value.includes('studio')) return '🛋️';
    if (value.includes('villa')) return '🏡';
    if (value.includes('maison')) return '🏠';
    if (value.includes('terrain')) return '🌍';
    if (value.includes('local')) return '🏬';
    if (value.includes('bureau')) return '💼';

    return '📍';
  }

  getPropertyBadge(property: PropertyItem): string {
    const ppm2 = property.price_per_m2 ?? 0;
    const surface = this.getPropertySurface(property) ?? 0;
    const rooms = property.rooms ?? property.room_count ?? 0;

    if (ppm2 > 0 && ppm2 < 120) return 'Best Value';
    if (surface >= 200) return 'Spacious';
    if (rooms >= 4) return 'Family Choice';
    return 'Selected';
  }

  getTransactionBadgeClass(value: string | null | undefined): string {
    const v = String(value || '').toLowerCase();
    if (v.includes('louer')) return 'rent';
    if (v.includes('vendre')) return 'sale';
    return 'default';
  }

  getPropertySurface(property: PropertyItem): number | null {
    return property.surface_m2 ?? property.size ?? null;
  }

  getPropertyRooms(property: PropertyItem): number | null {
    return property.rooms ?? property.room_count ?? null;
  }

  getPropertyBathrooms(property: PropertyItem): number | null {
    return property.bathrooms ?? property.bathroom_count ?? null;
  }

  getPricePerM2Label(property: PropertyItem): string {
    if (property.price_per_m2 === null || property.price_per_m2 === undefined) {
      return '-';
    }
    return `${this.formatPrice(property.price_per_m2)}/m²`;
  }

  hasListingUrl(property: PropertyItem): boolean {
    return !!(property.listing_url || property.url);
  }

  getListingUrl(property: PropertyItem): string {
    return property.listing_url || property.url || '#';
  }

  clearConversation(): void {
    this.messages = [];
    this.lastResponse = null;
    this.properties = [];
    this.errorMessage = '';
    this.userPrompt = '';
  }

  trackByMessage(index: number, item: ChatMessage): string {
    return `${item.role}-${index}-${item.content}`;
  }

  trackByPropertyId(index: number, item: PropertyItem): string {
    return item.id;
  }
}