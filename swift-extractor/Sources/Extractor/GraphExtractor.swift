import Foundation
import SwiftSyntax
import SwiftParser

class GraphExtractor {
    private(set) var symbols = [String: SymbolNode]()
    private(set) var edges = Set<SymbolEdge>()
    private var externalExclusions = Set<String>()

    func extract(from projectURL: URL, externalExclusionsFile: String?) throws {
        // 1. 외부 제외 목록 로드 (리소스, 헤더 등)
        if let path = externalExclusionsFile {
            loadExternalExclusions(from: path)
        }

        // 2. Plist 및 Storyboard/XIB 분석하여 클래스 이름 목록 확보
        print("  - Analyzing Plist and Storyboard files...")
        let plistAnalyzer = PlistAnalyzer()
        let storyboardAnalyzer = StoryboardAnalyzer()
        let fileBasedExclusions = plistAnalyzer.analyze(projectURL: projectURL)
            .union(storyboardAnalyzer.analyze(projectURL: projectURL))

        // 두 제외 목록을 합침
        self.externalExclusions.formUnion(fileBasedExclusions)

        // 3. Swift 소스 파일 분석
        print("  - Analyzing Swift source files...")
        let fileManager = FileManager.default
        let enumerator = fileManager.enumerator(
            at: projectURL,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles, .skipsPackageDescendants]
        )!

        for case let fileURL as URL in enumerator where fileURL.pathExtension == "swift" {
            let sourceText = try String(contentsOf: fileURL, encoding: .utf8)
            let visitor = SymbolVisitor(sourceText: sourceText, fileURL: fileURL)
            visitor.walk(Parser.parse(source: sourceText))

            // 심볼을 저장하면서 외부 참조 여부를 태그
            for var symbol in visitor.symbols {
                if externalExclusions.contains(symbol.name) {
                    symbol.isReferencedByExternalFile = true
                }
                self.symbols[symbol.id] = symbol
            }
            visitor.edges.forEach { self.edges.insert($0) }
        }

        // 4. 관계 해석 (상속, 오버라이드 등)
        resolveEdgeReferences()
    }

    private func loadExternalExclusions(from path: String) {
        print("  - Loading external exclusion list from: \(path)")
        do {
            let fileURL = URL(fileURLWithPath: path)
            let content = try String(contentsOf: fileURL, encoding: .utf8)
            let names = content.split(whereSeparator: \.isNewline).map(String.init)
            self.externalExclusions = Set(names)
            print("  - Loaded \(externalExclusions.count) external identifiers.")
        } catch {
            print("  - ⚠️ Warning: Could not load external exclusion list. \(error.localizedDescription)")
        }
    }

    private func resolveEdgeReferences() {
        print("  - Resolving symbol references...")
        var finalEdges = Set<SymbolEdge>()
        let symbolsByName = Dictionary(grouping: symbols.values, by: { $0.name })

        for edge in edges {
            if symbols[edge.to] != nil { // 이미 ID로 연결된 경우
                finalEdges.insert(edge)
                continue
            }

            if edge.to.hasPrefix("TYPE:") {
                let name = String(edge.to.dropFirst(5))
                if let target = symbolsByName[name]?.first { // 프로젝트 내부 타입
                    finalEdges.insert(SymbolEdge(from: edge.from, to: target.id, type: edge.type))
                } else { // 시스템 심볼로 간주
                    let systemId = "system-type-\(name)"
                    if symbols[systemId] == nil {
                        symbols[systemId] = SymbolNode(id: systemId, name: name, kind: .unknown, attributes: [], modifiers: [], isSystemSymbol: true)
                    }
                    finalEdges.insert(SymbolEdge(from: edge.from, to: systemId, type: edge.type))
                }
            } else if edge.to.hasPrefix("METHOD:") {
                let name = String(edge.to.dropFirst(7))
                if let parentMethodId = findParentMethod(childMethodId: edge.from, methodName: name) {
                    finalEdges.insert(SymbolEdge(from: edge.from, to: parentMethodId, type: .overrides))
                }
            }
        }
        self.edges = finalEdges
    }

    private func findParentMethod(childMethodId: String, methodName: String) -> String? {
        // [수정] 미사용 변수 경고를 해결하기 위해 'childMethod'를 '_'로 변경
        guard let _ = symbols[childMethodId],
              let classId = edges.first(where: { $0.to == childMethodId && $0.type == .contains })?.from else {
            return nil
        }

        let inheritedTypeIds = edges.filter { $0.from == classId && $0.type == .inheritsFrom }.map { $0.to }

        for inheritedTypeId in inheritedTypeIds {
            guard let inheritedType = symbols[inheritedTypeId] else { continue }

            if inheritedType.isSystemSymbol {
                let systemMethodId = "system-method-\(inheritedType.name)-\(methodName)"
                if symbols[systemMethodId] == nil {
                    let systemMethod = SymbolNode(id: systemMethodId, name: methodName, kind: .method, attributes: [], modifiers: [], isSystemSymbol: true)
                    symbols[systemMethodId] = systemMethod
                    edges.insert(SymbolEdge(from: inheritedTypeId, to: systemMethodId, type: .contains))
                }
                return systemMethodId
            } else {
                for edge in edges where edge.from == inheritedTypeId && edge.type == .contains {
                    if let method = symbols[edge.to], method.name == methodName {
                        return method.id
                    }
                }
            }
        }
        return nil
    }
}