import Foundation

struct SymbolGraph: Codable {
    var metadata: Metadata
    var symbols: [SymbolNode]
    var edges: [SymbolEdge]
}

struct Metadata: Codable {
    let projectPath: String
    let analyzedAt: String
}

struct SymbolNode: Codable, Hashable, Identifiable {
    let id: String
    var name: String
    var kind: SymbolKind
    var location: SourceLocation?
    var attributes: [String]
    var modifiers: [String]
    var isSystemSymbol: Bool = false

    // [추가] 리소스, 헤더 등 외부 파일에서 참조되는지 여부
    var isReferencedByExternalFile: Bool = false
}

struct SymbolEdge: Codable, Hashable {
    let from: String
    let to: String
    let type: EdgeType
}

struct SourceLocation: Codable, Hashable {
    let file: String
    let line: Int
    let column: Int
}

enum SymbolKind: String, Codable, Hashable {
    case `class`, `struct`, `enum`, `protocol`, `method`, property, function, unknown
}

enum EdgeType: String, Codable, Hashable {
    case inheritsFrom = "INHERITS_FROM"
    case conformsTo = "CONFORMS_TO"
    case overrides = "OVERRIDES"
    case contains = "CONTAINS"
}