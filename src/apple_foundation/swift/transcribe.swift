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

func ensureModel(transcriber: SpeechTranscriber, locale: Locale) async throws {
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
        print("Model for \(localeID) already installed.")
        return
    }

    print("Downloading speech model for \(localeID)...")
    if let downloader = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
        try await downloader.downloadAndInstall()
        print("Model downloaded successfully.")
    }
}

func streamAudioFile(
    url: URL,
    to inputBuilder: AsyncStream<AnalyzerInput>.Continuation,
    format: AVAudioFormat,
    progressTracker: ProgressTracker
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
        if percent != lastReportedPercent && percent % 10 == 0 {
            print("Progress: \(percent)%")
            lastReportedPercent = percent
        }
    }
}

func transcribeFile(at url: URL, locale: Locale) async throws -> String {
    print("Setting up transcriber for: \(locale.identifier(.bcp47))")

    // Create transcriber with audioTimeRange for word-level timestamps
    let transcriber = SpeechTranscriber(
        locale: locale,
        transcriptionOptions: [],
        reportingOptions: [],  // No volatile results for CLI
        attributeOptions: [.audioTimeRange]
    )

    // Ensure model is available
    try await ensureModel(transcriber: transcriber, locale: locale)

    // Get best audio format
    guard let analyzerFormat = await SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith: [transcriber]) else {
        throw TranscriptionError.noAudioFormat
    }

    print("Starting transcription...")

    // Create analyzer
    let analyzer = SpeechAnalyzer(modules: [transcriber])

    // Create input stream
    let (inputSequence, inputBuilder) = AsyncStream<AnalyzerInput>.makeStream()

    let progressTracker = ProgressTracker()
    let textAccumulator = TextAccumulator()

    // Start collecting results
    let resultsTask = Task {
        for try await result in transcriber.results {
            if result.isFinal {
                await textAccumulator.append(result.text)
            }
        }
    }

    // Start analyzer
    try await analyzer.start(inputSequence: inputSequence)

    // Stream audio file
    try await streamAudioFile(
        url: url,
        to: inputBuilder,
        format: analyzerFormat,
        progressTracker: progressTracker
    )

    // Finish streaming
    inputBuilder.finish()
    try await analyzer.finalizeAndFinishThroughEndOfInput()

    // Wait for results
    try? await resultsTask.value

    return await textAccumulator.plainText
}

// MARK: - Main

@main
struct TranscribeCLI {
    static func main() async {
        let args = CommandLine.arguments

        guard args.count >= 3 else {
            print("Usage: transcribe <input_audio_path> <output_text_path> [locale]")
            print("  locale: Optional, defaults to en-US")
            exit(1)
        }

        let inputPath = args[1]
        let outputPath = args[2]
        let localeIdentifier = args.count >= 4 ? args[3] : "en-US"

        let audioURL = URL(fileURLWithPath: inputPath)
        let outputURL = URL(fileURLWithPath: outputPath)

        // Use Locale components like Apple's sample
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
            let startTime = Date()

            let transcription = try await transcribeFile(at: audioURL, locale: locale)

            let elapsed = Date().timeIntervalSince(startTime)
            print(String(format: "\nTranscription completed in %.1f seconds", elapsed))

            if transcription.isEmpty {
                fputs("Warning: No speech detected in audio file\n", stderr)
            }

            try transcription.write(to: outputURL, atomically: true, encoding: String.Encoding.utf8)
            print("Saved to: \(outputPath)")

            let preview = String(transcription.prefix(300))
            print("\nPreview:\n\(preview)...")

        } catch {
            fputs("Error: \(error.localizedDescription)\n", stderr)
            exit(1)
        }
    }
}
