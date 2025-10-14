import Foundation
import ArgumentParser

@main
struct SymbolExtractor: ParsableCommand {
    static var configuration = CommandConfiguration(
        commandName: "SymbolExtractor",
        abstract: "A tool to extract symbols and their relationships from a Swift project."
    )

    @Argument(help: "Path to the Swift project directory.")
    var projectPath: String

    @Option(name: .shortAndLong, help: "Output path for the symbol_graph.json file.")
    var output: String = "symbol_graph.json"

    func run() throws {
        print("🔍 Starting extraction from: \(projectPath)...")
        let projectURL = URL(fileURLWithPath: projectPath)

        let extractor = GraphExtractor()
        try extractor.extract(from: projectURL)

        print("✅ Found \(extractor.symbols.count) symbols and \(extractor.edges.count) relationships.")

        let graph = SymbolGraph(
            metadata: Metadata(
                projectPath: projectPath,
                analyzedAt: ISO8_601DateFormatter.string(from: Date(), timeZone: .current, formatOptions: .withInternetDateTime)
            ),
            symbols: Array(extractor.symbols.values),
            edges: Array(extractor.edges)
        )

        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted
        let jsonData = try encoder.encode(graph)

        let outputURL = URL(fileURLWithPath: output)
        try jsonData.write(to: outputURL)

        print("🎉 Successfully exported symbol graph to: \(outputURL.path)")
    }
}

// Swift 5.7+ 에서는 ISO8601DateFormatter.string(from:) 사용
// 하위 호환성을 위해 직접 구현
class ISO8_601DateFormatter {
    private static let formatter = ISO8601DateFormatter()

    static func string(from date: Date, timeZone: TimeZone, formatOptions: ISO8601DateFormatter.Options) -> String {
        formatter.timeZone = timeZone
        formatter.formatOptions = formatOptions
        return formatter.string(from: date)
    }
}