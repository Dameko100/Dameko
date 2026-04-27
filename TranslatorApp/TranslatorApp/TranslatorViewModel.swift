import SwiftUI
import Combine

enum Language: String, CaseIterable {
    case english = "en"
    case spanish = "es"

    var displayName: String {
        switch self {
        case .english: return "Inglés"
        case .spanish: return "Español"
        }
    }
}

@MainActor
class TranslatorViewModel: ObservableObject {
    @Published var inputText: String = ""
    @Published var translatedText: String = ""
    @Published var sourceLanguage: Language = .english
    @Published var targetLanguage: Language = .spanish
    @Published var isLoading: Bool = false
    @Published var errorMessage: String? = nil
    @Published var copied: Bool = false

    private var autoTranslateTask: Task<Void, Never>?

    func translate() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        isLoading = true
        errorMessage = nil

        do {
            let result = try await TranslationService.translate(
                text,
                from: sourceLanguage.rawValue,
                to: targetLanguage.rawValue
            )
            translatedText = result
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func swapLanguages() {
        let temp = sourceLanguage
        sourceLanguage = targetLanguage
        targetLanguage = temp
        let tempText = inputText
        inputText = translatedText
        translatedText = tempText
    }

    func copyTranslation() {
        UIPasteboard.general.string = translatedText
        withAnimation {
            copied = true
        }
        Task {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            withAnimation { copied = false }
        }
    }

    // Auto-translate 0.8s after user stops typing
    func scheduleAutoTranslate() {
        autoTranslateTask?.cancel()
        autoTranslateTask = Task {
            try? await Task.sleep(nanoseconds: 800_000_000)
            guard !Task.isCancelled else { return }
            await translate()
        }
    }
}
