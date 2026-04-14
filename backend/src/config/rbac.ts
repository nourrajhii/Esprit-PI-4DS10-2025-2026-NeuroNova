export type UserRole =
  | 'individual_investor'
  | 'professional_investor'
  | 'real_estate_agency'
  | 'developer_fund'

// Professional permissions (simple defaults you can tune later).
// You said earlier: role 4 (developer_fund) = YES.
export const PERMISSIONS = {
  canPublish: ['professional_investor', 'real_estate_agency', 'developer_fund'] as UserRole[],
  canEditOwnListing: ['professional_investor', 'real_estate_agency', 'developer_fund'] as UserRole[],
  canDeleteOwnListing: ['professional_investor', 'real_estate_agency', 'developer_fund'] as UserRole[],
  canUploadListingImages: ['professional_investor', 'real_estate_agency', 'developer_fund'] as UserRole[],
  canUseLegalAssistant: ['professional_investor', 'real_estate_agency', 'developer_fund'] as UserRole[],
  canUse3DJobs: ['professional_investor', 'real_estate_agency', 'developer_fund'] as UserRole[],
}

