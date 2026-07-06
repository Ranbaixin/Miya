import Foundation

// MARK: - API 服务

actor MiyaAPIService {
    private var baseURL: String
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: String = "http://localhost:8000") {
        self.baseURL = baseURL
        self.session = URLSession.shared
        self.decoder = JSONDecoder()
    }

    func updateBaseURL(_ url: String) {
        baseURL = url
    }

    // MARK: - 健康检查

    func healthCheck() async -> Bool {
        do {
            let (_, response) = try await session.data(from: url("/health"))
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - 聊天

    func sendMessage(_ message: String, sessionId: String?) async throws -> String {
        var body: [String: Any] = ["message": message, "platform": "ios"]
        if let sid = sessionId { body["session_id"] = sid }

        let data = try await post("/api/chat/send", body: body)
        let response = try decoder.decode(ChatResponse.self, from: data)
        return response.reply ?? ""
    }

    func streamChat(_ message: String, sessionId: String?) -> AsyncThrowingStream<String, Error> {
        AsyncThrowingStream { continuation in
            Task {
                var body: [String: Any] = ["message": message, "platform": "ios"]
                if let sid = sessionId { body["session_id"] = sid }

                var request = URLRequest(url: url("/api/chat"))
                request.httpMethod = "POST"
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                request.httpBody = try? JSONSerialization.data(withJSONObject: body)

                do {
                    let (bytes, _) = try await session.bytes(for: request)
                    for try await line in bytes.lines {
                        if line.hasPrefix("data: ") {
                            let data = String(line.dropFirst(6))
                            if data == "[DONE]" {
                                continuation.finish()
                                return
                            }
                            if let chunk = data.data(using: .utf8),
                               let json = try? JSONSerialization.jsonObject(with: chunk) as? [String: Any],
                               let choices = json["choices"] as? [[String: Any]],
                               let delta = choices.first?["delta"] as? [String: Any],
                               let content = delta["content"] as? String {
                                continuation.yield(content)
                            }
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    func stopChat() async {
        _ = try? await post("/api/chat/stop", body: [:])
    }

    func getSessions() async throws -> [MiyaSession] {
        let data = try await get("/api/chat/sessions")
        return try decoder.decode([MiyaSession].self, from: data)
    }

    func newSession() async throws -> String {
        struct NewSession: Codable { let id: String }
        let data = try await get("/api/chat/new_session")
        let result = try decoder.decode(NewSession.self, from: data)
        return result.id
    }

    // MARK: - 记忆

    func getMemoryList(limit: Int = 50) async throws -> [MemoryItem] {
        struct ListResponse: Codable { let results: [MemoryItem] }
        let data = try await get("/api/memory/list?limit=\(limit)")
        let result = try decoder.decode(ListResponse.self, from: data)
        return result.results
    }

    func searchMemory(_ query: String, limit: Int = 20) async throws -> [MemoryItem] {
        struct ListResponse: Codable { let results: [MemoryItem] }
        let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        let data = try await get("/api/memory/search?query=\(encoded)&limit=\(limit)")
        let result = try decoder.decode(ListResponse.self, from: data)
        return result.results
    }

    // MARK: - 人格

    func getPersonaList() async throws -> [MiyaPersona] {
        struct ListResponse: Codable { let personalities: [MiyaPersona] }
        let data = try await get("/api/persona/list")
        let result = try decoder.decode(ListResponse.self, from: data)
        return result.personalities
    }

    func getCurrentPersona() async throws -> String {
        struct CurrentResponse: Codable {
            let id: String?
            let current: String?
        }
        let data = try await get("/api/persona/current")
        let result = try decoder.decode(CurrentResponse.self, from: data)
        return result.id ?? result.current ?? "default"
    }

    func getPersonas() async throws -> [MiyaPersona] { try await getPersonaList() }
    func getCurrentPersonaId() async throws -> String { try await getCurrentPersona() }
    func switchPersona(_ personaId: String) async throws -> Bool {
        let body: [String: Any] = ["personality_id": personaId]
        let data = try await post("/api/persona/switch", body: body)
        struct SwitchResponse: Codable { let success: Bool }
        let result = try decoder.decode(SwitchResponse.self, from: data)
        return result.success
    }

    // MARK: - 语音转文字

    func transcribeAudio(_ audioData: Data, language: String = "zh") async throws -> String? {
        let boundary = UUID().uuidString
        var request = URLRequest(url: url("/api/audio/transcribe"))
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio\"; filename=\"recording.wav\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body
        let (data, _) = try await session.data(for: request)
        let result = try decoder.decode(TranscribeResponse.self, from: data)
        return result.text
    }

    struct TranscribeResponse: Codable { let text: String? }
    struct ChatResponse: Codable { let reply: String? }

    // MARK: - 系统状态

    func getSystemStatus() async throws -> SystemStatusInfo {
        let data = try await get("/api/status")
        return try decoder.decode(SystemStatusInfo.self, from: data)
    }

    func getMemoryStats() async throws -> MemoryStatsInfo {
        let data = try await get("/api/memory/stats")
        return try decoder.decode(MemoryStatsInfo.self, from: data)
    }

    // MARK: - 私有请求方法

    private func url(_ path: String) -> URL {
        URL(string: "\(baseURL)\(path)")!
    }

    private func get(_ path: String) async throws -> Data {
        let (data, response) = try await session.data(from: url(path))
        if let http = response as? HTTPURLResponse, http.statusCode >= 400 {
            throw URLError(.badServerResponse)
        }
        return data
    }

    private func post(_ path: String, body: [String: Any]) async throws -> Data {
        var request = URLRequest(url: url(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode >= 400 {
            throw URLError(.badServerResponse)
        }
        return data
    }
}
