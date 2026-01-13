import Foundation
import Speech
import AVFoundation

// MARK: - Errors

enum TranscriptionError: LocalizedError {
    case localeNotSupported
    case noSupportedLocales
    case noAudioFormat
    case fileNotFound(String)
    case transcriptionFailed(String)

    var errorDescription: String? {
        switch self {
        case .localeNotSupported: return "Language not supported"
        case .noSupportedLocales: return "Speech transcription not available"
        case .noAudioFormat: return "Could not determine audio format"
        case .fileNotFound(let path): return "File not found: \(path)"
        case .transcriptionFailed(let msg): return "Transcription failed: \(msg)"
        }
    }
}

// MARK: - Buffer Converter

final class BufferConverter: @unchecked Sendable {
    private var converter: AVAudioConverter?

    func convertBuffer(_ buffer: AVAudioPCMBuffer, to format: AVAudioFormat) throws -> AVAudioPCMBuffer {
        let inputFormat = buffer.format
        guard inputFormat != format else { return buffer }

        if converter == nil || converter?.outputFormat != format {
            converter = AVAudioConverter(from: inputFormat, to: format)
            converter?.primeMethod = .none
        }

        guard let converter else {
            throw NSError(domain: "BufferConverter", code: 1, userInfo: [NSLocalizedDescriptionKey: "Failed to create converter"])
        }

        let sampleRateRatio = converter.outputFormat.sampleRate / converter.inputFormat.sampleRate
        let scaledInputFrameLength = Double(buffer.frameLength) * sampleRateRatio
        let frameCapacity = AVAudioFrameCount(scaledInputFrameLength.rounded(.up))

        guard let conversionBuffer = AVAudioPCMBuffer(pcmFormat: converter.outputFormat, frameCapacity: frameCapacity) else {
            throw NSError(domain: "BufferConverter", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create buffer"])
        }

        var processed = false
        var nsError: NSError?

        let status = converter.convert(to: conversionBuffer, error: &nsError) { _, inputStatusPointer in
            if processed {
                inputStatusPointer.pointee = .noDataNow
                return nil
            }
            processed = true
            inputStatusPointer.pointee = .haveData
            return buffer
        }

        if status == .error {
            throw nsError ?? NSError(domain: "BufferConverter", code: 3, userInfo: [NSLocalizedDescriptionKey: "Conversion failed"])
        }

        return conversionBuffer
    }
}

// MARK: - Progress Tracker

actor ProgressTracker {
    private(set) var progress: Double = 0

    func setProgress(_ value: Double) {
        progress = value
    }
}

// MARK: - Text Accumulator

actor TextAccumulator {
    private var text = AttributedString()

    func append(_ newText: AttributedString) {
        text += newText
    }

    var currentText: AttributedString { text }
    var plainText: String { String(text.characters) }
}

// MARK: - Transcription

// MARK: - Models

struct TranscriptionSegment: Codable {
    let text: String
    let start: Double?
    let duration: Double?
    let confidence: Double?
}

struct TranscriptionResult: Codable {
    let text: String
    let segments: [TranscriptionSegment]
    let alternatives: [String]?
}

// MARK: - Helper Extensions

extension SpeechTranscriber.Result {
    func toTranscriptionResult(includeSegments: Bool, includeAlternatives: Bool) -> TranscriptionResult {
        var segments: [TranscriptionSegment] = []
        
        if includeSegments {
            for run in self.text.runs {
                let segmentText = String(self.text[run.range].characters)
                
                var start: Double?
                var duration: Double?
                var confidence: Double?
                
                if let timeRange = run.attributes[AttributeScopes.SpeechAttributes.TimeRangeAttribute.self] {
                    start = timeRange.start.seconds
                    duration = timeRange.duration.seconds
                }
                
                if let conf = run.attributes[AttributeScopes.SpeechAttributes.ConfidenceAttribute.self] {
                    confidence = conf
                }
                
                if !segmentText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    segments.append(TranscriptionSegment(
                        text: segmentText,
                        start: start,
                        duration: duration,
                        confidence: confidence
                    ))
                }
            }
        }
        
        var alts: [String]? = nil
        if includeAlternatives {
            alts = self.alternatives.map { String($0.characters) }
        }
        
        return TranscriptionResult(
            text: String(self.text.characters),
            segments: segments.isEmpty ? [] : segments,
            alternatives: alts
        )
    }
}

extension TranscriptionResult {
    func toJSONString() -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = .sortedKeys
        if let data = try? encoder.encode(self), let jsonIdx = String(data: data, encoding: .utf8) {
             return jsonIdx
        }
        return "{}"
    }
}

actor TranscriptionAccumulator {
    private var fullText = ""
    private var allSegments: [TranscriptionSegment] = []
    private var allAlternatives: [String] = []

    func append(_ result: TranscriptionResult) {
        fullText += result.text
        allSegments.append(contentsOf: result.segments)
        if let alts = result.alternatives {
            allAlternatives.append(contentsOf: alts)
        }
    }
    
    var finalResult: TranscriptionResult {
        TranscriptionResult(
            text: fullText,
            segments: allSegments,
            alternatives: allAlternatives.isEmpty ? nil : allAlternatives
        )
    }
}

// MARK: - Main

@main
struct TranscribeCLI {
    static func main() async {
        let args = CommandLine.arguments
        
        guard args.count >= 2 else {
            printUsage()
            exit(1)
        }

        let inputPath = args[1]
        var localeIdentifier = "en-US"
        var fast = false
        var redact = false
        var stream = false
        var json = false
        var confidence = false
        var alternatives = false
        
        var i = 2
        while i < args.count {
            let arg = args[i]
            switch arg {
            case "--locale":
                if i + 1 < args.count {
                    localeIdentifier = args[i+1]
                    i += 1
                }
            case "--fast":
                fast = true
            case "--redact":
                redact = true
            case "--stream":
                stream = true
            case "--json":
                json = true
            case "--confidence":
                confidence = true
            case "--alternatives":
                alternatives = true
            default:
                break
            }
            i += 1
        }

        let audioURL = URL(fileURLWithPath: inputPath)

        let parts = localeIdentifier.split(separator: "-")
        let langCode = String(parts[0])
        let regionCode = parts.count > 1 ? String(parts[1]) : "US"

        let locale = Locale(components: .init(
            languageCode: .init(langCode),
            script: nil,
            languageRegion: .init(regionCode)
        ))

        guard FileManager.default.fileExists(atPath: inputPath) else {
            fputs("Error: Input file not found: \(inputPath)\n", stderr)
            exit(1)
        }

        do {
            let transcription = try await transcribeFile(
                at: audioURL,
                locale: locale,
                fast: fast,
                redact: redact,
                stream: stream,
                json: json,
                confidence: confidence,
                alternatives: alternatives
            )

            if !stream {
                 print(transcription)
            }

        } catch {
            fputs("Error: \(error.localizedDescription)\n", stderr)
            exit(1)
        }
    }
    
    static func printUsage() {
        print("""
        Usage: transcribe <input_audio_path> [options]
        
        Options:
          --locale <locale>   Locale code (e.g. en-US), default: en-US
          --fast              Use fast transcription (lower accuracy)
          --redact            Redact sensitive info (politics/swear words based on etiquette)
          --stream            Stream partial results to stdout
          --json              Output structured JSON
          --confidence        Include confidence scores (JSON only)
          --alternatives      Include alternative transcriptions (JSON only)
        """)
    }

    // MARK: - Transcription Logic

    static func transcribeFile(
        at url: URL,
        locale: Locale,
        fast: Bool,
        redact: Bool,
        stream: Bool,
        json: Bool,
        confidence: Bool,
        alternatives: Bool
    ) async throws -> String {

        var reportingOptions: Set<SpeechTranscriber.ReportingOption> = []
        if fast {
            reportingOptions.insert(.fastResults)
        }
        if stream {
            reportingOptions.insert(.volatileResults)
        }
        if alternatives {
            reportingOptions.insert(.alternativeTranscriptions)
        }

        var transcriptionOptions: Set<SpeechTranscriber.TranscriptionOption> = []
        if redact {
            transcriptionOptions.insert(.etiquetteReplacements)
        }
        
        var attributeOptions: Set<SpeechTranscriber.ResultAttributeOption> = [.audioTimeRange]
        if confidence {
            attributeOptions.insert(.transcriptionConfidence)
        }

        let transcriber = SpeechTranscriber(
            locale: locale,
            transcriptionOptions: transcriptionOptions,
            reportingOptions: reportingOptions,
            attributeOptions: attributeOptions
        )

        try await ensureModel(transcriber: transcriber, locale: locale, quiet: json)

        guard let analyzerFormat = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [transcriber]) else {
            throw TranscriptionError.noAudioFormat
        }

        let analyzer = SpeechAnalyzer(modules: [transcriber])
        let (inputSequence, inputBuilder) = AsyncStream<AnalyzerInput>.makeStream()

        let progressTracker = ProgressTracker()
        let accumulator = TranscriptionAccumulator()

        let resultsTask = Task {
            for try await result in transcriber.results {
                if stream {
                    if json {
                        let tr = result.toTranscriptionResult(includeSegments: true, includeAlternatives: alternatives)
                        print(tr.toJSONString()) 
                        if !stream { fflush(stdout) }
                    } else {
                        print(result.text.characters.map { String($0) }.joined(), terminator: "\r")
                        fflush(stdout)
                    }
                }
                
                if result.isFinal {
                    let tr = result.toTranscriptionResult(includeSegments: true, includeAlternatives: alternatives)
                    await accumulator.append(tr)
                    
                    if stream && !json {
                        print("", terminator: "\n")
                    }
                }
            }
        }

        try await analyzer.start(inputSequence: inputSequence)

        try await streamAudioFile(
            url: url,
            to: inputBuilder,
            format: analyzerFormat,
            progressTracker: progressTracker,
            quiet: json
        )

        inputBuilder.finish()
        try await analyzer.finalizeAndFinishThroughEndOfInput()

        _ = try? await resultsTask.value
        
        if json {
            return await accumulator.finalResult.toJSONString()
        } else {
            return await accumulator.finalResult.text
        }
    }

    static func ensureModel(transcriber: SpeechTranscriber, locale: Locale, quiet: Bool) async throws {
        let supported = await SpeechTranscriber.supportedLocales
        let localeID = locale.identifier(.bcp47)
        let supportedIDs = supported.map { $0.identifier(.bcp47) }

        guard !supportedIDs.isEmpty else {
            throw TranscriptionError.noSupportedLocales
        }

        guard supportedIDs.contains(localeID) else {
            throw TranscriptionError.localeNotSupported
        }

        let installed = await Set(SpeechTranscriber.installedLocales)
        let installedIDs = installed.map { $0.identifier(.bcp47) }

        if installedIDs.contains(localeID) {
            return
        }

        if !quiet { print("Downloading speech model for \(localeID)...") }
        if let downloader = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
            try await downloader.downloadAndInstall()
            if !quiet { print("Model downloaded successfully.") }
        }
    }

    static func streamAudioFile(
        url: URL,
        to inputBuilder: AsyncStream<AnalyzerInput>.Continuation,
        format: AVAudioFormat,
        progressTracker: ProgressTracker,
        quiet: Bool
    ) async throws {
        let file = try AVAudioFile(forReading: url)
        let totalFrames = file.length

        var framesRead: AVAudioFramePosition = 0
        let bufferSize: AVAudioFrameCount = 4096
        let converter = BufferConverter()

        var lastReportedPercent = -1

        while framesRead < totalFrames {
            try Task.checkCancellation()

            let framesToRead = min(bufferSize, AVAudioFrameCount(totalFrames - framesRead))
            guard let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: framesToRead) else {
                continue
            }

            try file.read(into: buffer)
            framesRead += AVAudioFramePosition(buffer.frameLength)

            let converted = try converter.convertBuffer(buffer, to: format)
            let input = AnalyzerInput(buffer: converted)
            inputBuilder.yield(input)

            let progress = Double(framesRead) / Double(totalFrames)
            await progressTracker.setProgress(progress)

            let percent = Int(progress * 100)
            if !quiet && percent != lastReportedPercent && percent % 10 == 0 {
                lastReportedPercent = percent
            }
        }
    }
}
