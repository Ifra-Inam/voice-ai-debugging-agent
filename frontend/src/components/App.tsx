import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react'
import { submitDebugSession } from '../services/debugApi'
import './App.css'

function Chatbot() {
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string>('')
  const [audioUrl, setAudioUrl] = useState('')
  const [responseAudioUrl, setResponseAudioUrl] = useState('')
  const [answer, setAnswer] = useState('')
  const [transcript, setTranscript] = useState('')
  const [errorText, setErrorText] = useState('')
  const [sources, setSources] = useState<string[]>([])
  const [toolCalls, setToolCalls] = useState<string[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('Add a screenshot and record a short voice note.')

  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  const stopRecording = () => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }

    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop()
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }

    setIsRecording(false)
  }

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus('This browser does not support microphone recording.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      const chunks: BlobPart[] = []

      recorderRef.current = recorder
      streamRef.current = stream

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data)
      }

      recorder.onstop = async () => {
        try {
          const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
          const wavBlob = await convertToWav(blob)
          const file = new File([wavBlob], 'voice-input.wav', { type: 'audio/wav' })

          if (audioUrl) URL.revokeObjectURL(audioUrl)
          setAudioFile(file)
          setAudioUrl(URL.createObjectURL(file))
          setStatus('Voice note saved. Ready to send.')
        } catch {
          setStatus('Could not process the recording. Try again.')
        }

        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop())
          streamRef.current = null
        }

        recorderRef.current = null
        setIsRecording(false)
      }

      recorder.start()
      setIsRecording(true)
      setStatus('Recording. Click again to stop (30 second limit).')

      timerRef.current = window.setTimeout(() => {
        if (recorder.state !== 'inactive') {
          recorder.stop()
        }
      }, 30000)
    } catch (error) {
      setIsRecording(false)
      setStatus(error instanceof Error ? error.message : 'Microphone access was denied.')
    }
  }

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null

    if (imagePreview) URL.revokeObjectURL(imagePreview)

    setImageFile(file)
    setImagePreview(file ? URL.createObjectURL(file) : '')
  }

  const handleSubmit = async () => {
    if (!audioFile || !imageFile) {
      setStatus('Add a screenshot and record your message first.')
      return
    }

    setLoading(true)
    setSources([])
    setToolCalls([])
    setStatus('Tool calling: transcribing audio, reading screenshot text, and debugging the issue…')

    try {
      const result = await submitDebugSession(audioFile, imageFile)
      setTranscript(result.transcript)
      setErrorText(result.error)
      setAnswer(result.answer)
      setSources(result.sources ?? [])
      setToolCalls(result.tool_calls ?? [])
      setResponseAudioUrl(`data:audio/mpeg;base64,${result.audio_data}`)
      setStatus('Response ready.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Unable to submit debug request.')
    } finally {
      setLoading(false)
    }
  }

  const canSend = !loading && !!audioFile && !!imageFile
  const sessionState = isRecording ? 'rec' : loading ? 'busy' : answer ? 'done' : 'idle'
  const stateLabel = { rec: 'RECORDING', busy: 'ANALYZING', done: 'READY', idle: 'IDLE' }[sessionState]

  return (
    <div className="dbg">
      <header className="dbg-titlebar">
        <h1 className="dbg-title">debug-assistant</h1>
        <p className="dbg-subtitle">screenshot + voice note, one session</p>
      </header>

      <div className="dbg-body">
        <aside className="dbg-side">
          <section className="dbg-section">
            <h2 className="dbg-section-title">Screenshot</h2>
            <div className={imagePreview ? 'dbg-drop has-image' : 'dbg-drop'}>
              <input
                id="image-upload"
                className="dbg-drop-input"
                type="file"
                accept="image/*"
                aria-label="Upload a screenshot"
                onChange={handleImageChange}
              />
              {imagePreview ? (
                <img className="dbg-preview" src={imagePreview} alt="Selected screenshot" />
              ) : (
                <>
                  <svg className="dbg-drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <rect x="3" y="4" width="18" height="16" rx="2" />
                    <circle cx="8.5" cy="9.5" r="1.5" />
                    <path d="M21 16l-5-5-8 9" />
                  </svg>
                  <span className="dbg-drop-main">Choose or drop a screenshot</span>
                  <span className="dbg-drop-hint">png, jpg, webp</span>
                </>
              )}
            </div>
            {imageFile && (
              <div className="dbg-file-line">
                <span className="dbg-file-name">{imageFile.name}</span>
                <span>click image to replace</span>
              </div>
            )}
          </section>

          <section className="dbg-section">
            <h2 className="dbg-section-title">Voice note</h2>
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              className={isRecording ? 'dbg-record is-active' : 'dbg-record'}
            >
              <span className="dbg-bp" aria-hidden="true" />
              {isRecording ? 'Stop recording' : audioFile ? 'Record again' : 'Start recording'}
              <span className="dbg-record-limit" aria-hidden="true" />
            </button>
            {audioFile && !isRecording && (
              <>
                <div className="dbg-file-line">
                  <span className="dbg-file-name">{audioFile.name}</span>
                  <span>saved</span>
                </div>
                <div className="dbg-audio-wrap">
                  <audio className="dbg-audio dbg-audio--voice" controls src={audioUrl} />
                </div>
              </>
            )}
          </section>

          <section className="dbg-section">
            <button type="button" onClick={handleSubmit} disabled={!canSend} className="dbg-run">
              <svg viewBox="0 0 12 12" fill="currentColor" aria-hidden="true"><path d="M2 1l9 5-9 5z" /></svg>
              {loading ? 'Analyzing…' : 'Run debug session'}
            </button>
          </section>
        </aside>

        <main className="dbg-main" aria-busy={loading}>
          <Pane
            name="transcript.txt"
            modifier="transcript"
            text={transcript}
            empty="// waiting for a voice note"
          />
          <Pane
            name="response.md"
            modifier="response"
            text={answer}
            empty="// the assistant's answer will appear here"
          >
            {responseAudioUrl && <audio className="dbg-audio" controls autoPlay src={responseAudioUrl} />}
            {toolCalls.length > 0 && (
              <div className="dbg-meta-card">
                <div className="dbg-meta-header">Tools used</div>
                <ul className="dbg-meta-list">
                  {toolCalls.map((tool, index) => (
                    <li key={`${tool}-${index}`}>{tool}</li>
                  ))}
                </ul>
              </div>
            )}
            {sources.length > 0 && (
              <div className="dbg-meta-card">
                <div className="dbg-meta-header">Sources used</div>
                <ul className="dbg-meta-list">
                  {sources.map((source, index) => (
                    <li key={`${source}-${index}`}>
                      <a href={source} target="_blank" rel="noreferrer">{source}</a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Pane>
          <Pane
            name="screenshot.ocr"
            modifier="ocr"
            text={errorText}
            empty="// text read from your screenshot will appear here"
          />
        </main>
      </div>

      <footer className={`dbg-status dbg-status--${sessionState}`}>
        <div className="dbg-status-main">
          <span className="dbg-state">{stateLabel}</span>
          <p className="dbg-message" role="status" aria-live="polite">{status}</p>
        </div>
        <div className="dbg-status-side">
          <span>screenshot: {imageFile ? 'attached' : 'none'}</span>
          <span>voice: {audioFile ? 'attached' : 'none'}</span>
        </div>
      </footer>
    </div>
  )
}

function renderInlineMarkdown(value: string) {
  const chunks = value.split(/(\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|`[^`]+`)/g)

  return chunks.map((chunk, index) => {
    if (!chunk) return null

    if (chunk.startsWith('**') && chunk.endsWith('**')) {
      return <strong key={index}>{chunk.slice(2, -2)}</strong>
    }

    if (chunk.startsWith('__') && chunk.endsWith('__')) {
      return <strong key={index}>{chunk.slice(2, -2)}</strong>
    }

    if (chunk.startsWith('*') && chunk.endsWith('*') && !chunk.startsWith('**')) {
      return <em key={index}>{chunk.slice(1, -1)}</em>
    }

    if (chunk.startsWith('_') && chunk.endsWith('_') && !chunk.startsWith('__')) {
      return <em key={index}>{chunk.slice(1, -1)}</em>
    }

    if (chunk.startsWith('`') && chunk.endsWith('`')) {
      return <code key={index} className="dbg-inline-code">{chunk.slice(1, -1)}</code>
    }

    return <Fragment key={index}>{chunk}</Fragment>
  })
}

function Pane({
  name,
  modifier,
  text,
  empty,
  children,
}: {
  name: string
  modifier: string
  text: string
  empty: string
  children?: ReactNode
}) {
  if (modifier === 'response') {
    const lines = (text || empty).split(/\r?\n/)
    const blocks: React.ReactNode[] = []
    let paragraph: string[] = []
    let listItems: string[] = []
    let codeLines: string[] = []
    let codeLanguage = ''
    let inCodeBlock = false

    const flushParagraph = () => {
      if (paragraph.length) {
        blocks.push(
          <p className="dbg-response-paragraph" key={`p-${blocks.length}`}>
            {renderInlineMarkdown(paragraph.join(' '))}
          </p>,
        )
        paragraph = []
      }
    }

    const flushList = () => {
      if (listItems.length) {
        blocks.push(
          <ul className="dbg-response-list" key={`list-${blocks.length}`}>
            {listItems.map((item, index) => (
              <li key={`${item}-${index}`}>{renderInlineMarkdown(item)}</li>
            ))}
          </ul>,
        )
        listItems = []
      }
    }

    const flushCode = () => {
      if (codeLines.length) {
        blocks.push(
          <pre key={`code-${blocks.length}`} className="dbg-response-code-block">
            <code className={`language-${codeLanguage || 'text'}`}>{codeLines.join('\n')}</code>
          </pre>,
        )
        codeLines = []
      }
      codeLanguage = ''
      inCodeBlock = false
    }

    lines.forEach((line) => {
      const trimmed = line.trim()

      if (line.startsWith('```')) {
        flushParagraph()
        flushList()

        if (inCodeBlock) {
          flushCode()
          return
        }

        inCodeBlock = true
        codeLanguage = line.slice(3).trim()
        return
      }

      if (inCodeBlock) {
        codeLines.push(line)
        return
      }

      if (!trimmed) {
        flushParagraph()
        flushList()
        return
      }

      if (/^#{1,3}\s+/.test(line)) {
        flushParagraph()
        flushList()
        blocks.push(
          <h3 key={`h-${blocks.length}`} className="dbg-response-heading">
            {renderInlineMarkdown(trimmed.replace(/^#{1,3}\s+/, ''))}
          </h3>,
        )
        return
      }

      if (/^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line)) {
        flushParagraph()
        listItems.push(trimmed.replace(/^[-*]\s+|^\d+\.\s+/, ''))
        return
      }

      paragraph.push(trimmed)
    })

    flushParagraph()
    flushList()
    if (inCodeBlock) flushCode()

    return (
      <section className={`dbg-pane dbg-pane--${modifier}`}>
        <div className="dbg-tabbar">
          <span className="dbg-tab">{name}</span>
          <span className="dbg-meta">{text ? 'ready' : 'empty'}</span>
        </div>
        <div className="dbg-pane-body">
          <div className={text ? 'dbg-response-content' : 'dbg-response-content is-empty'}>
            {text ? blocks : <div className="dbg-response-empty">{empty}</div>}
          </div>
          {children}
        </div>
      </section>
    )
  }

  const lines = (text || empty).split('\n')

  return (
    <section className={`dbg-pane dbg-pane--${modifier}`}>
      <div className="dbg-tabbar">
        <span className="dbg-tab">{name}</span>
        <span className="dbg-meta">{text ? `${lines.length} ${lines.length === 1 ? 'line' : 'lines'}` : 'empty'}</span>
      </div>
      <div className="dbg-pane-body">
        <div className={text ? 'dbg-code' : 'dbg-code is-empty'}>
          {lines.map((line, i) => (
            <div className="dbg-line" key={i}>
              <span className="dbg-ln">{i + 1}</span>
              <span className="dbg-lc">{line}</span>
            </div>
          ))}
        </div>
        {children}
      </div>
    </section>
  )
}

async function convertToWav(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer()
  const audioContext = new AudioContext()
  const decoded = await audioContext.decodeAudioData(arrayBuffer.slice(0))

  const numberOfChannels = decoded.numberOfChannels
  const sampleRate = decoded.sampleRate
  const format = 1
  const bitDepth = 16

  const samples = decoded.length
  const bytesPerSample = bitDepth / 8
  const blockAlign = numberOfChannels * bytesPerSample
  const dataLength = samples * blockAlign
  const buffer = new ArrayBuffer(44 + dataLength)
  const view = new DataView(buffer)

  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataLength, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, format, true)
  view.setUint16(22, numberOfChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, bitDepth, true)
  writeString(view, 36, 'data')
  view.setUint32(40, dataLength, true)

  let offset = 44
  const channelData = Array.from({ length: numberOfChannels }, (_, channel) => decoded.getChannelData(channel))

  for (let i = 0; i < samples; i += 1) {
    for (let channel = 0; channel < numberOfChannels; channel += 1) {
      const sample = Math.max(-1, Math.min(1, channelData[channel][i]))
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
      offset += 2
    }
  }

  await audioContext.close()

  return new Blob([buffer], { type: 'audio/wav' })
}

function writeString(view: DataView, offset: number, value: string) {
  for (let i = 0; i < value.length; i += 1) {
    view.setUint8(offset + i, value.charCodeAt(i))
  }
}

export default Chatbot