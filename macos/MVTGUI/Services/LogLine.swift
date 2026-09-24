import Foundation

/// Severity of a console line, derived from the prefix MVT's log handler
/// prints (see `MVTLogHandler` in src/mvt/common/log.py).
enum LogLevel: Int, Comparable, CaseIterable {
    case plain
    case command
    case warning
    case error
    case infoAlert
    case lowAlert
    case mediumAlert
    case highAlert
    case criticalAlert

    static func < (lhs: LogLevel, rhs: LogLevel) -> Bool { lhs.rawValue < rhs.rawValue }

    var isAlert: Bool { self >= .infoAlert }

    private static let prefixes: [(String, LogLevel)] = [
        ("CRITICAL ALERT", .criticalAlert),
        ("HIGH ALERT", .highAlert),
        ("MEDIUM ALERT", .mediumAlert),
        ("LOW ALERT", .lowAlert),
        ("INFO ALERT", .infoAlert),
        ("WARNING", .warning),
        ("ERROR", .error),
        ("FATAL", .error),
        ("Error:", .error),
        ("Traceback", .error),
    ]

    static func classify(_ line: String) -> LogLevel {
        for (prefix, level) in prefixes where line.hasPrefix(prefix) {
            return level
        }
        return .plain
    }
}

struct LogLine: Identifiable {
    let id: Int
    let text: String
    let level: LogLevel
}

enum ANSI {
    private static let regex = try! NSRegularExpression(
        pattern: "\u{1B}\\[[0-9;?]*[ -/]*[@-~]|\u{1B}\\][^\u{07}]*\u{07}"
    )

    static func strip(_ s: String) -> String {
        guard s.contains("\u{1B}") else { return s }
        let range = NSRange(s.startIndex..., in: s)
        return regex.stringByReplacingMatches(in: s, range: range, withTemplate: "")
    }
}
