export type DebugApiResponse = {
  transcript: string
  error: string
  answer: string
  audio_data: string
  sources?: string[]
  tool_calls?: string[]
}

export async function submitDebugSession(audioFile: File, imageFile: File) {
  const formData = new FormData()
  formData.append('audio', audioFile, audioFile.name || 'audio.wav')
  formData.append('screenshot', imageFile, imageFile.name || 'screenshot.png')

  const response = await fetch('http://localhost:8000/api/debug', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || 'Failed to submit debug request')
  }

  return (await response.json()) as DebugApiResponse
}
