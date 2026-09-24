import Foundation

/// One set of public indicators: a STIX2 file from one of the sources.
struct IndicatorSet: Identifiable, Hashable {
    let name: String
    let sources: [String]
    let references: [URL]
    let downloadURL: URL
    /// Listed in MVT's own index, so `mvt download-iocs` fetches it too.
    var inMVTIndex = true

    var id: String { downloadURL.absoluteString }

    /// The file name MVT itself gives this set when it downloads it
    /// (download_remote_ioc in src/mvt/common/updates.py), so that a set
    /// downloaded here and by `mvt download-iocs` ends up in the same file.
    var localFileName: String {
        // Python's str.lstrip("https://") strips any of those characters.
        let stripped = Set("https:/")
        let url = downloadURL.absoluteString
        return String(url.drop(while: { stripped.contains($0) }))
            .replacingOccurrences(of: "/", with: "_")
    }

    var localURL: URL {
        IndicatorsIndex.folder.appendingPathComponent(localFileName)
    }
}

/// Reads the official list of public indicators and manages the downloaded
/// files that MVT loads automatically.
enum IndicatorsIndex {
    /// The index `mvt download-iocs` reads (IndicatorsUpdates in updates.py).
    static let indexURL = URL(string: "https://raw.githubusercontent.com/mvt-project/mvt-indicators/main/indicators.yaml")!

    /// Where MVT keeps downloaded indicators: appdirs' user_data_dir("mvt").
    static var folder: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("mvt/indicators", isDirectory: true)
    }

    enum Failure: LocalizedError {
        case http(Int, URL)

        var errorDescription: String? {
            switch self {
            case let .http(status, url):
                return "The server answered \(status) for \(url.absoluteString)."
            }
        }
    }

    static func fetch() async throws -> [IndicatorSet] {
        let text = try await get(indexURL)
        return parse(String(decoding: text, as: UTF8.self))
    }

    // MARK: - Source repositories

    /// The repositories public indicators come from. MVT's index lists most
    /// of their files; any STIX2 file it doesn't list is added from here.
    struct SourceRepository {
        let owner: String
        let repo: String
        let branch: String
        let organization: String

        var webURL: URL { URL(string: "https://github.com/\(owner)/\(repo)")! }
    }

    static let sourceRepositories = [
        SourceRepository(owner: "mvt-project", repo: "mvt-indicators", branch: "main", organization: "MVT project"),
        SourceRepository(owner: "AmnestyTech", repo: "investigations", branch: "master", organization: "Amnesty International"),
        SourceRepository(owner: "AssoEchap", repo: "stalkerware-indicators", branch: "master", organization: "Echap"),
    ]

    /// STIX2 files in the source repositories that MVT's index doesn't list,
    /// used when GitHub can't be asked (it allows 60 anonymous listings an
    /// hour). Keep in sync with the repositories.
    static let knownExtraFiles = [
        (repo: "AmnestyTech/investigations", path: "2021-12-16_cytrox/cytrox.stix2"),
    ]

    /// Every STIX2 file in the source repositories that isn't already in
    /// `known`, named after its folder.
    static func extraSets(excluding known: [IndicatorSet]) async -> [IndicatorSet] {
        let knownURLs = Set(known.map(\.downloadURL))
        var found: [(SourceRepository, String)] = []
        var listedAll = true
        for source in sourceRepositories {
            if let paths = try? await stix2Paths(in: source) {
                found += paths.map { (source, $0) }
            } else {
                listedAll = false
            }
        }
        if !listedAll {
            for extra in knownExtraFiles {
                guard let source = sourceRepositories.first(where: { "\($0.owner)/\($0.repo)" == extra.repo }),
                      !found.contains(where: { $0.0.repo == source.repo && $0.1 == extra.path }) else { continue }
                found.append((source, extra.path))
            }
        }
        return found.compactMap { source, path -> IndicatorSet? in
            let url = URL(string: "https://raw.githubusercontent.com/\(source.owner)/\(source.repo)/\(source.branch)/\(path)")!
            guard !knownURLs.contains(url) else { return nil }
            let folder = (path as NSString).deletingLastPathComponent
            return IndicatorSet(
                name: displayName(forPath: path),
                sources: [source.organization],
                references: [source.webURL.appendingPathComponent("tree/\(source.branch)/\(folder)")],
                downloadURL: url,
                inMVTIndex: false
            )
        }
    }

    private static func stix2Paths(in source: SourceRepository) async throws -> [String] {
        let url = URL(string: "https://api.github.com/repos/\(source.owner)/\(source.repo)/git/trees/\(source.branch)?recursive=1")!
        let data = try await get(url)
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let tree = json["tree"] as? [[String: Any]] else { return [] }
        return tree.compactMap { $0["path"] as? String }
            .filter { $0.lowercased().hasSuffix(".stix2") }
    }

    /// "2021-12-16_cytrox/cytrox.stix2" → "Cytrox indicators (2021-12-16)".
    static func displayName(forPath path: String) -> String {
        let folder = (path as NSString).deletingLastPathComponent
        var words = (folder.isEmpty ? (path as NSString).lastPathComponent : folder)
            .replacingOccurrences(of: ".stix2", with: "")
            .split(separator: "_")
            .map(String.init)
        var date: String?
        if let first = words.first, first.range(of: #"^\d{4}-\d{2}(-\d{2})?$"#, options: .regularExpression) != nil {
            date = first
            words.removeFirst()
        }
        let title = words.map { $0.prefix(1).uppercased() + $0.dropFirst() }.joined(separator: " ")
        return "\(title.isEmpty ? "Unnamed" : title) indicators" + (date.map { " (\($0))" } ?? "")
    }

    /// Downloads one set into the indicators folder, where every check
    /// picks it up.
    @discardableResult
    static func download(_ set: IndicatorSet) async throws -> URL {
        let data = try await get(set.downloadURL)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        try data.write(to: set.localURL, options: .atomic)
        return set.localURL
    }

    /// Indicator files MVT loads automatically: only `.stix2` files in the
    /// folder (_load_downloaded_indicators in src/mvt/common/indicators.py).
    static func downloadedFiles() -> [URL] {
        let files = (try? FileManager.default.contentsOfDirectory(
            at: folder, includingPropertiesForKeys: nil, options: [.skipsHiddenFiles]
        )) ?? []
        return files
            .filter { $0.pathExtension.lowercased() == "stix2" }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    private static func get(_ url: URL) async throws -> Data {
        var request = URLRequest(url: url)
        request.timeoutInterval = 30
        let (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw Failure.http(http.statusCode, url)
        }
        return data
    }

    // MARK: - Parsing

    /// Parses indicators.yaml. The file is a flat list of entries with
    /// `type`, `name`, `sources`, `references` and either a `github` block
    /// or a `download_url`; this reads exactly that shape and resolves
    /// download URLs the way IndicatorsUpdates.update() does.
    static func parse(_ text: String) -> [IndicatorSet] {
        struct Entry {
            var fields: [String: String] = [:]
            var github: [String: String] = [:]
            var sources: [String] = []
            var references: [String] = []
        }

        var entries: [Entry] = []
        var section: String?

        for raw in text.components(separatedBy: .newlines) {
            let trimmedStart = raw.drop(while: { $0 == " " })
            if trimmedStart.hasPrefix("#") { continue }
            var line = raw
            if let comment = line.range(of: " #") { line = String(line[..<comment.lowerBound]) }
            line = String(line.reversed().drop(while: { $0 == " " || $0 == "\t" }).reversed())
            guard !line.trimmingCharacters(in: .whitespaces).isEmpty else { continue }

            var indent = line.prefix(while: { $0 == " " }).count
            var body = line.trimmingCharacters(in: .whitespaces)
            if body == "indicators:" { continue }

            if body.hasPrefix("-") && indent <= 2 {
                entries.append(Entry())
                section = nil
                let rest = body.dropFirst().trimmingCharacters(in: .whitespaces)
                if rest.isEmpty { continue }
                body = rest
                indent = 4
            }
            guard !entries.isEmpty else { continue }

            if body.hasPrefix("- ") {
                let item = unquote(String(body.dropFirst(2)))
                if section == "sources" { entries[entries.count - 1].sources.append(item) }
                if section == "references" { entries[entries.count - 1].references.append(item) }
                continue
            }
            guard let colon = body.firstIndex(of: ":") else { continue }
            let key = body[..<colon].trimmingCharacters(in: .whitespaces)
            let value = unquote(String(body[body.index(after: colon)...]))

            if indent <= 4 {
                section = value.isEmpty ? key : nil
                if !value.isEmpty { entries[entries.count - 1].fields[key] = value }
            } else if section == "github" {
                entries[entries.count - 1].github[key] = value
            }
        }

        return entries.compactMap { entry -> IndicatorSet? in
            let urlString: String
            if entry.fields["type"] == "github" {
                let g = entry.github
                guard let owner = g["owner"], let repo = g["repo"], let path = g["path"],
                      !owner.isEmpty, !repo.isEmpty, !path.isEmpty else { return nil }
                urlString = "https://raw.githubusercontent.com/\(owner)/\(repo)/\(g["branch"] ?? "main")/\(path)"
            } else {
                urlString = entry.fields["download_url"] ?? ""
            }
            guard let url = URL(string: urlString), url.scheme == "https" else { return nil }
            return IndicatorSet(
                name: entry.fields["name"] ?? url.lastPathComponent,
                sources: entry.sources,
                references: entry.references.compactMap { URL(string: $0) },
                downloadURL: url
            )
        }
    }

    private static func unquote(_ value: String) -> String {
        let v = value.trimmingCharacters(in: .whitespaces)
        if v.count >= 2, let first = v.first, first == v.last, first == "'" || first == "\"" {
            return String(v.dropFirst().dropLast())
        }
        return v
    }
}

/// App-wide state for the Indicators screen and the indicator picker.
@MainActor
final class IndicatorStore: ObservableObject {
    @Published private(set) var sets: [IndicatorSet] = []
    @Published private(set) var downloaded: [URL] = IndicatorsIndex.downloadedFiles()
    @Published private(set) var isLoadingIndex = false
    @Published private(set) var indexError: String?
    /// IDs of sets currently downloading.
    @Published private(set) var downloading: Set<String> = []
    @Published var lastError: String?

    func refreshDownloaded() {
        downloaded = IndicatorsIndex.downloadedFiles()
    }

    func loadIndex() async {
        guard !isLoadingIndex else { return }
        isLoadingIndex = true
        defer { isLoadingIndex = false }
        var loaded: [IndicatorSet] = []
        do {
            loaded = try await IndicatorsIndex.fetch()
            indexError = nil
        } catch {
            indexError = "Couldn't load MVT's official list: \(error.localizedDescription)"
        }
        // Files in the source repositories that MVT's list doesn't include.
        loaded += await IndicatorsIndex.extraSets(excluding: loaded)
        sets = loaded
    }

    func isDownloaded(_ set: IndicatorSet) -> Bool {
        downloaded.contains { $0.lastPathComponent == set.localFileName }
    }

    func download(_ sets: [IndicatorSet]) async {
        for set in sets where !downloading.contains(set.id) {
            downloading.insert(set.id)
            do {
                try await IndicatorsIndex.download(set)
            } catch {
                lastError = "Couldn't download “\(set.name)”: \(error.localizedDescription)"
            }
            downloading.remove(set.id)
            refreshDownloaded()
        }
    }

    /// Copies a STIX2 file into the indicators folder so every check uses it.
    /// MVT only loads files ending in .stix2 from there.
    func importFile(_ url: URL) {
        var name = url.lastPathComponent
        if url.pathExtension.lowercased() != "stix2" { name += ".stix2" }
        let destination = IndicatorsIndex.folder.appendingPathComponent(name)
        do {
            try FileManager.default.createDirectory(at: IndicatorsIndex.folder, withIntermediateDirectories: true)
            if FileManager.default.fileExists(atPath: destination.path) {
                try FileManager.default.removeItem(at: destination)
            }
            try FileManager.default.copyItem(at: url, to: destination)
        } catch {
            lastError = "Couldn't import \(url.lastPathComponent): \(error.localizedDescription)"
        }
        refreshDownloaded()
    }

    func moveToTrash(_ url: URL) {
        do {
            try FileManager.default.trashItem(at: url, resultingItemURL: nil)
        } catch {
            lastError = "Couldn't remove \(url.lastPathComponent): \(error.localizedDescription)"
        }
        refreshDownloaded()
    }

    /// A readable name for a downloaded file: the set's name when the file
    /// came from the official list.
    func displayName(for url: URL) -> String {
        sets.first { $0.localFileName == url.lastPathComponent }?.name
            ?? url.deletingPathExtension().lastPathComponent
    }
}
