import type { ArtGenerateResult, ArtImageEntry, ArtProviderInfo, ArtStats } from '@/types/art'
import { ApiClient } from './index'

export class ArtApiClient extends ApiClient {
  async getProviders(): Promise<{ success: boolean, providers: ArtProviderInfo[] }> {
    return this.instance.get('/api/art/providers')
  }

  async refreshProviders(): Promise<{ success: boolean, providers: ArtProviderInfo[] }> {
    return this.instance.get('/api/art/providers/refresh')
  }

  async generate(params: {
    prompt: string
    provider?: string
    negativePrompt?: string
    width?: number
    height?: number
    steps?: number
    cfgScale?: number
    seed?: number | null
    numImages?: number
    style?: string
  }): Promise<ArtGenerateResult> {
    return this.instance.post('/api/art/generate', params)
  }

  async getGallery(params: {
    provider?: string
    limit?: number
    offset?: number
  } = {}): Promise<{ success: boolean, images: ArtImageEntry[], total: number }> {
    return this.instance.get('/api/art/gallery', { params })
  }

  async deleteImage(imageId: string): Promise<{ success: boolean }> {
    return this.instance.delete(`/api/art/image/${imageId}`)
  }

  async clearGallery(): Promise<{ success: boolean, deleted: number }> {
    return this.instance.delete('/api/art/gallery/clear')
  }

  async getStats(): Promise<{ success: boolean, stats: ArtStats }> {
    return this.instance.get('/api/art/stats')
  }

const API_PORT = Number(import.meta.env.VITE_API_PORT) || 9800

  getImageUrl(filename: string): string {
    return `http://localhost:${API_PORT}/api/art/image/${filename}`
  }
}

export default new ArtApiClient(API_PORT)
