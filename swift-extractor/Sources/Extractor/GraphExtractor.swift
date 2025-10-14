import Foundation
import SwiftSyntax
import SwiftParser

class GraphExtractor {
    private(set) var symbols = [String: SymbolNode]()
    private(set) var edges = Set<SymbolEdge>()

    func extract(from projectURL: URL) throws {
        let fileManager = FileManager.default
        let enumerator = fileManager.enumerator(
            at: projectURL,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles, .skipsPackageDescendants]
        )!

        // 1. Swift 파일 분석
        print("  - Analyzing Swift source files...")
        for case let fileURL as URL in enumerator where fileURL.pathExtension == "swift" {
            let sourceText = try String(contentsOf: fileURL, encoding: .utf8)
            let visitor = SymbolVisitor(sourceText: sourceText, fileURL: fileURL)
            visitor.walk(Parser.parse(source: sourceText))

            visitor.symbols.forEach { self.symbols[$0.id] = $0 }
            visitor.edges.forEach { self.edges.insert($0) }
        }

        // 2. 관계(엣지)의 이름 기반 참조를 ID 기반 참조로 변환
        resolveEdgeReferences()

        // 3. 외부 파일(Plist, Storyboard) 분석
        print("  - Analyzing Plist and Storyboard files...")
        let plistAnalyzer = PlistAnalyzer()
        let storyboardAnalyzer = StoryboardAnalyzer()

        let fileReferences = plistAnalyzer.analyze(projectURL: projectURL)
            .merging(storyboardAnalyzer.analyze(projectURL: projectURL)) { (_, new) in new }

        for (className, fileURL) in fileReferences {
            if let symbol = symbols.values.first(where: { $0.name == className && $0.kind == .class }) {
                let edge = SymbolEdge(from: symbol.id, to: fileURL.lastPathComponent, type: .referencedByFile)
                edges.insert(edge)
            }
        }
    }

    private func resolveEdgeReferences() {
        print("  - Resolving symbol references...")
        var resolvedEdges = Set<SymbolEdge>()
        let symbolsByName = Dictionary(grouping: symbols.values, by: { $0.name })

        for edge in edges {
            // 이미 ID 기반이면 그대로 추가
            if symbols[edge.to] != nil {
                resolvedEdges.insert(edge)
                continue
            }

            let targetName = edge.to

            // TYPE: 또는 METHOD: 프리픽스 처리
            if targetName.hasPrefix("TYPE:") {
                let actualName = String(targetName.dropFirst(5))
                if let targetSymbols = symbolsByName[actualName],
                   let targetSymbol = targetSymbols.first(where: { $0.kind != .method && $0.kind != .property }) {
                    // 프로젝트 내 타입과 연결
                    resolvedEdges.insert(SymbolEdge(from: edge.from, to: targetSymbol.id, type: edge.type))
                } else {
                    // 시스템 심볼로 간주
                    let systemSymbolId = "system-\(actualName)"
                    if symbols[systemSymbolId] == nil {
                        let newSymbol = SymbolNode(
                            id: systemSymbolId,
                            name: actualName,
                            kind: .unknown,
                            attributes: [],
                            modifiers: [],
                            isSystemSymbol: true
                        )
                        self.symbols[systemSymbolId] = newSymbol
                    }
                    resolvedEdges.insert(SymbolEdge(from: edge.from, to: systemSymbolId, type: edge.type))
                }
            } else if targetName.hasPrefix("METHOD:") {
                let actualName = String(targetName.dropFirst(7))
                // 오버라이드 관계 해결: 부모 클래스에서 동일 이름 메서드 찾기
                if let childSymbol = symbols[edge.from] {
                    let parentMethod = findParentMethod(for: childSymbol, methodName: actualName)
                    if let parentMethodId = parentMethod?.id {
                        resolvedEdges.insert(SymbolEdge(from: edge.from, to: parentMethodId, type: .overrides))
                    }
                }
            } else {
                // 그 외의 경우 (파일 참조 등)
                resolvedEdges.insert(edge)
            }
        }
        self.edges = resolvedEdges
    }

    private func findParentMethod(for childSymbol: SymbolNode, methodName: String) -> SymbolNode? {
        // 1. 자식 심볼이 속한 부모 타입 찾기
        guard let parentTypeEdge = edges.first(where: { $0.to == childSymbol.id && $0.type == .contains }),
              let parentType = symbols[parentTypeEdge.from] else {
            return nil
        }

        // 2. 부모 타입이 상속/채택하는 타입들 찾기
        let inheritedTypes = edges
            .filter { $0.from == parentType.id && $0.type == .inheritsFrom }
            .compactMap { symbols[$0.to] }

        // 3. 상속된 타입들에서 동일 이름의 메서드 찾기
        for inheritedType in inheritedTypes {
            let methodEdges = edges.filter { $0.from == inheritedType.id && $0.type == .contains }
            for methodEdge in methodEdges {
                if let method = symbols[methodEdge.to],
                   method.kind == .method,
                   method.name == methodName {
                    return method
                }
            }
        }

        return nil
    }
}