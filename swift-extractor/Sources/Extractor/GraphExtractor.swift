import Foundation
import SwiftSyntax
import SwiftParser

class GraphExtractor {
    private(set) var symbols = [String: SymbolNode]()
    private(set) var edges = Set<SymbolEdge>()
    private var externalExclusions = Set<String>()

    func extract(from projectURL: URL, externalExclusionsFile: String?) throws {
        // 1. 외부 제외 목록 로드
        if let path = externalExclusionsFile {
            loadExternalExclusions(from: path)
        }

        // 2. Plist 및 Storyboard 분석
        print("  - Analyzing Plist and Storyboard files...")
        let plistAnalyzer = PlistAnalyzer()
        let storyboardAnalyzer = StoryboardAnalyzer()
        let fileBasedExclusions = plistAnalyzer.analyze(projectURL: projectURL)
            .union(storyboardAnalyzer.analyze(projectURL: projectURL))
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
            let sourceTree = Parser.parse(source: sourceText)
            visitor.walk(sourceTree)

            for var symbol in visitor.symbols {
                if externalExclusions.contains(symbol.name) {
                    symbol.isReferencedByExternalFile = true
                }
                self.symbols[symbol.id] = symbol
            }
            visitor.edges.forEach { self.edges.insert($0) }
        }

        // 4. 관계 해석 및 상속 체인 빌드
        resolveRelationships()
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

    private func resolveRelationships() {
        print("  - Resolving symbol references...")

        // 1단계: 모든 타입 이름에 대해 시스템 심볼 노드 생성 (정보 확장)
        ensureSystemSymbolsExist()

        // 2단계: 이름 기반 엣지를 ID 기반으로 해석
        resolveNamedEdges()

        // 3단계: 클래스 상속과 프로토콜 채택을 모두 포함하여 상속 체인 빌드
        buildInheritanceAndConformanceChains()

        // 4단계: 멤버들에게 상속 체인 정보 전파
        propagateChainsToMembers()
    }

    // [✨ 추가] 모든 `typeName`을 분석하여 시스템 심볼을 미리 생성하는 함수
    private func ensureSystemSymbolsExist() {
        let allTypeNames = Set(symbols.values.compactMap { $0.typeName })
        let symbolsByName = Dictionary(grouping: symbols.values, by: { $0.name })

        for typeName in allTypeNames {
            let cleanTypeName = typeName.trimmingCharacters(in: .punctuationCharacters)
            if symbolsByName[cleanTypeName] == nil && symbols["system-\(cleanTypeName)"] == nil {
                let systemId = "system-\(cleanTypeName)"
                symbols[systemId] = SymbolNode(id: systemId, name: cleanTypeName, kind: .unknown, attributes: [], modifiers: [], isSystemSymbol: true)
            }
        }
    }

    private func resolveNamedEdges() {
        var finalEdges = Set<SymbolEdge>()
        let symbolsByName = Dictionary(grouping: symbols.values, by: { $0.name })

        for edge in edges {
            if symbols[edge.to] != nil {
                finalEdges.insert(edge)
                continue
            }

            let name: String
            if edge.to.hasPrefix("TYPE:") {
                name = String(edge.to.dropFirst(5))
            } else if edge.to.hasPrefix("METHOD:") {
                name = String(edge.to.dropFirst(7))
            } else {
                finalEdges.insert(edge)
                continue
            }

            if let target = symbolsByName[name]?.first {
                finalEdges.insert(SymbolEdge(from: edge.from, to: target.id, type: edge.type))
            } else {
                let systemId = "system-\(name)"
                if symbols[systemId] == nil {
                    symbols[systemId] = SymbolNode(id: systemId, name: name, kind: .unknown, attributes: [], modifiers: [], isSystemSymbol: true)
                }
                finalEdges.insert(SymbolEdge(from: edge.from, to: systemId, type: edge.type))
            }
        }
        self.edges = finalEdges
    }

    // [✨ 수정] 클래스 상속과 프로토콜 채택을 모두 처리하도록 이름과 로직 변경
    private func buildInheritanceAndConformanceChains() {
        var chainCache = [String: [String]]()

        func getChain(for symbolId: String) -> [String] {
            if let cached = chainCache[symbolId] {
                return cached
            }
            guard let symbol = symbols[symbolId] else { return [] }

            var chain = [String]()
            // ✨ 클래스 상속과 프로토콜 채택 엣지를 모두 사용
            let parentEdges = edges.filter { $0.from == symbolId && ($0.type == .inheritsFrom || $0.type == .conformsTo) }

            for edge in parentEdges {
                guard let parentSymbol = symbols[edge.to] else { continue }
                chain.append(parentSymbol.name)
                chain.append(contentsOf: getChain(for: parentSymbol.id))
            }

            let uniqueChain = Array(NSOrderedSet(array: chain)) as! [String]
            chainCache[symbolId] = uniqueChain
            return uniqueChain
        }

        for id in symbols.keys {
            let chain = getChain(for: id)
            if !chain.isEmpty {
                symbols[id]?.typeInheritanceChain = chain
            }
        }
    }

    // [✨ 수정] 함수 이름 변경
    private func propagateChainsToMembers() {
        let parentChildEdges = edges.filter { $0.type == .contains }
        let classLikeSymbols = symbols.values.filter { $0.kind == .class || $0.kind == .struct }

        for symbol in classLikeSymbols {
            guard let chain = symbol.typeInheritanceChain else { continue }

            // BFS/DFS로 모든 자식 심볼을 순회하며 상속 체인 전파
            var queue = [symbol.id]
            var visited = Set<String>()

            while !queue.isEmpty {
                let currentId = queue.removeFirst()
                if visited.contains(currentId) { continue }
                visited.insert(currentId)

                let childrenIds = parentChildEdges.filter { $0.from == currentId }.map { $0.to }
                for childId in childrenIds {
                    if symbols[childId]?.typeInheritanceChain == nil {
                         symbols[childId]?.typeInheritanceChain = chain
                    }
                    queue.append(childId)
                }
            }
        }
    }
}