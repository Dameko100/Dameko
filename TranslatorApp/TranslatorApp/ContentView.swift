import SwiftUI

struct ContentView: View {
    @StateObject private var vm = TranslatorViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                languageBar
                Divider()
                ScrollView {
                    VStack(spacing: 16) {
                        inputPanel
                        translateButton
                        outputPanel
                    }
                    .padding()
                }
            }
            .navigationTitle("Traductor")
            .navigationBarTitleDisplayMode(.inline)
            .background(Color(.systemGroupedBackground))
        }
    }

    // MARK: - Language bar

    private var languageBar: some View {
        HStack {
            languageLabel(vm.sourceLanguage.displayName)
            Spacer()
            Button(action: vm.swapLanguages) {
                Image(systemName: "arrow.left.arrow.right")
                    .font(.title3)
                    .foregroundColor(.accentColor)
                    .padding(8)
                    .background(Color(.systemBackground))
                    .clipShape(Circle())
                    .shadow(radius: 2)
            }
            Spacer()
            languageLabel(vm.targetLanguage.displayName)
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(.systemBackground))
    }

    private func languageLabel(_ name: String) -> some View {
        Text(name)
            .font(.headline)
            .frame(minWidth: 120)
            .multilineTextAlignment(.center)
    }

    // MARK: - Input

    private var inputPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(vm.sourceLanguage.displayName)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
                if !vm.inputText.isEmpty {
                    Button(action: { vm.inputText = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                }
            }

            TextEditor(text: $vm.inputText)
                .frame(minHeight: 130)
                .scrollContentBackground(.hidden)
                .onChange(of: vm.inputText) { _ in vm.scheduleAutoTranslate() }

            HStack {
                Spacer()
                Text("\(vm.inputText.count) caracteres")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }

    // MARK: - Button

    private var translateButton: some View {
        Button(action: { Task { await vm.translate() } }) {
            HStack(spacing: 8) {
                if vm.isLoading {
                    ProgressView()
                        .tint(.white)
                } else {
                    Image(systemName: "text.bubble.fill")
                }
                Text(vm.isLoading ? "Traduciendo..." : "Traducir")
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(vm.inputText.isEmpty ? Color.gray : Color.accentColor)
            .foregroundColor(.white)
            .cornerRadius(14)
        }
        .disabled(vm.inputText.isEmpty || vm.isLoading)
    }

    // MARK: - Output

    private var outputPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(vm.targetLanguage.displayName)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
                if !vm.translatedText.isEmpty {
                    Button(action: vm.copyTranslation) {
                        HStack(spacing: 4) {
                            Image(systemName: vm.copied ? "checkmark" : "doc.on.doc")
                            Text(vm.copied ? "Copiado" : "Copiar")
                        }
                        .font(.caption)
                        .foregroundColor(.accentColor)
                    }
                }
            }

            if vm.translatedText.isEmpty && !vm.isLoading {
                Text("La traducción aparecerá aquí...")
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, minHeight: 130, alignment: .topLeading)
            } else {
                Text(vm.translatedText)
                    .frame(maxWidth: .infinity, minHeight: 130, alignment: .topLeading)
                    .textSelection(.enabled)
            }

            if let error = vm.errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }
}

#Preview {
    ContentView()
}
