import SwiftSyntax
import Foundation

class SymbolVisitor: SyntaxVisitor {
    private(set) var symbols = [SymbolNode]()
    private(set) var edges = [SymbolEdge]()

    private let sourceLocationConverter: SourceLocationConverter
    private let fileURL: URL
    private var parentStack = [String]() // 부모 심볼의 ID 추적

    init(sourceText: String, fileURL: URL) {
        self.sourceLocationConverter = SourceLocationConverter(
            fileName: fileURL.path,
            tree: Parser.parse(source: sourceText)
        )
        self.fileURL = fileURL
        super.init(viewMode: .sourceAccurate)
    }

    private func location(for node: some SyntaxProtocol) -> SourceLocation {
        let location = node.startLocation(converter: sourceLocationConverter)
        return SourceLocation(
            file: fileURL.lastPathComponent,
            line: location.line ?? 0,
            column: location.column ?? 0
        )
    }

    override func visit(_ node: ClassDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: node.name.text, kind: .class, node: node)
        symbols.append(symbol)
        handleInheritance(for: id, from: node.inheritanceClause)
        handleContainment(childId: id)
        parentStack.append(id)
        return .visitChildren
    }

    override func visitPost(_ node: ClassDeclSyntax) {
        _ = parentStack.popLast()
    }

    override func visit(_ node: StructDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: node.name.text, kind: .struct, node: node)
        symbols.append(symbol)
        handleInheritance(for: id, from: node.inheritanceClause)
        handleContainment(childId: id)
        parentStack.append(id)
        return .visitChildren
    }

    override func visitPost(_ node: StructDeclSyntax) {
        _ = parentStack.popLast()
    }

    override func visit(_ node: EnumDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: node.name.text, kind: .enum, node: node)
        symbols.append(symbol)
        handleInheritance(for: id, from: node.inheritanceClause)
        handleContainment(childId: id)
        parentStack.append(id)
        return .visitChildren
    }

    override func visitPost(_ node: EnumDeclSyntax) {
        _ = parentStack.popLast()
    }

    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: node.name.text, kind: .method, node: node)
        symbols.append(symbol)
        handleContainment(childId: id)

        if symbol.modifiers.contains("override") {
            // 오버라이드된 메서드를 나중에 해결하기 위한 임시 엣지 생성
            // to 필드에 메서드 이름을 저장 (나중에 실제 ID로 변환됨)
            edges.append(SymbolEdge(from: id, to: "METHOD:\(symbol.name)", type: .overrides))
        }
        return .visitChildren
    }

    override func visit(_ node: VariableDeclSyntax) -> SyntaxVisitorContinueKind {
        for binding in node.bindings {
            if let pattern = binding.pattern.as(IdentifierPatternSyntax.self) {
                let id = UUID().uuidString
                let symbol = createSymbol(id: id, name: pattern.identifier.text, kind: .property, node: node)
                symbols.append(symbol)
                handleContainment(childId: id)
            }
        }
        return .visitChildren
    }

    // --- Helper Functions ---

    private func createSymbol<T: DeclSyntaxProtocol>(id: String, name: String, kind: SymbolKind, node: T) -> SymbolNode {
        let attributes = node.attributes.map {
            $0.trimmedDescription.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        let modifiers = node.modifiers.map {
            $0.name.text.trimmingCharacters(in: .whitespacesAndNewlines)
        }

        return SymbolNode(
            id: id,
            name: name,
            kind: kind,
            location: location(for: node),
            attributes: attributes,
            modifiers: modifiers
        )
    }

    private func handleContainment(childId: String) {
        if let parentId = parentStack.last {
            edges.append(SymbolEdge(from: parentId, to: childId, type: .contains))
        }
    }

    private func handleInheritance(for id: String, from clause: InheritanceClauseSyntax?) {
        guard let clause = clause else { return }
        for type in clause.inheritedTypes {
            let parentTypeName = type.type.trimmedDescription
            // 임시로 타입 이름을 저장 (나중에 실제 ID로 변환됨)
            let edge = SymbolEdge(from: id, to: "TYPE:\(parentTypeName)", type: .inheritsFrom)
            edges.append(edge)
        }
    }
}