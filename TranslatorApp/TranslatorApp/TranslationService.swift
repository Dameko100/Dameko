import Foundation

enum TranslationError: LocalizedError {
    case networkError(Error)
    case invalidResponse
    case apiError(String)

    var errorDescription: String? {
        switch self {
        case .networkError(let e): return "Error de red: \(e.localizedDescription)"
        case .invalidResponse: return "Respuesta inválida del servidor"
        case .apiError(let msg): return "Error de traducción: \(msg)"
        }
    }
}

struct TranslationService {
    // Uses MyMemory free API — no key required, 5000 words/day free
    static func translate(_ text: String, from source: String, to target: String) async throws -> String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "" }

        var components = URLComponents(string: "https://api.mymemory.translated.net/get")!
        components.queryItems = [
            URLQueryItem(name: "q", value: trimmed),
            URLQueryItem(name: "langpair", value: "\(source)|\(target)")
        ]

        guard let url = components.url else { throw TranslationError.invalidResponse }

        let (data, response) = try await URLSession.shared.data(from: url)

        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw TranslationError.invalidResponse
        }

        let decoded = try JSONDecoder().decode(MyMemoryResponse.self, from: data)

        guard decoded.responseStatus == 200 else {
            throw TranslationError.apiError(decoded.responseDetails ?? "Unknown error")
        }

        return decoded.responseData.translatedText
    }
}

private struct MyMemoryResponse: Decodable {
    let responseData: ResponseData
    let responseStatus: Int
    let responseDetails: String?

    struct ResponseData: Decodable {
        let translatedText: String
    }
}
