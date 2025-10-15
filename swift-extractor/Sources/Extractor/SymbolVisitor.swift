import SwiftSyntax
import SwiftParser
import Foundation

class SymbolVisitor: SyntaxVisitor {
    private(set) var symbols = [SymbolNode]()
    private(set) var edges = [SymbolEdge]()

    private let sourceLocationConverter: SourceLocationConverter
    private let fileURL: URL
    private var parentStack = [String]()

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
            line: location.line,
            column: location.column
        )
    }

    // --- Main Declarations ---

    override func visit(_ node: ClassDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: node.name.text, kind: .class, decl: node)
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
        let symbol = createSymbol(id: id, name: node.name.text, kind: .struct, decl: node)
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
        let symbol = createSymbol(id: id, name: node.name.text, kind: .enum, decl: node)
        symbols.append(symbol)
        handleInheritance(for: id, from: node.inheritanceClause)
        handleContainment(childId: id)
        parentStack.append(id)
        return .visitChildren
    }

    override func visitPost(_ node: EnumDeclSyntax) {
        _ = parentStack.popLast()
    }

    // --- Member Declarations ---

    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let returnTypeName = node.signature.returnClause?.type.trimmedDescription
        let symbol = createSymbol(id: id, name: node.name.text, kind: .method, decl: node, typeName: returnTypeName)
        symbols.append(symbol)
        handleContainment(childId: id)

        if symbol.modifiers.contains("override") {
            edges.append(SymbolEdge(from: id, to: "METHOD:\(symbol.name)", type: .overrides))
        }
        return .visitChildren
    }

    override func visit(_ node: VariableDeclSyntax) -> SyntaxVisitorContinueKind {
        for binding in node.bindings {
            if let pattern = binding.pattern.as(IdentifierPatternSyntax.self) {
                let id = UUID().uuidString
                let typeName = binding.typeAnnotation?.type.trimmedDescription
                let symbol = createSymbol(id: id, name: pattern.identifier.text, kind: .property, decl: node, typeName: typeName)
                symbols.append(symbol)
                handleContainment(childId: id)
            }
        }
        return .visitChildren
    }

    override func visit(_ node: InitializerDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: "init", kind: .initializer, decl: node)
        symbols.append(symbol)
        handleContainment(childId: id)

        if symbol.modifiers.contains("override") {
            edges.append(SymbolEdge(from: id, to: "METHOD:init", type: .overrides))
        }
        return .visitChildren
    }

    override func visit(_ node: OperatorDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: node.name.text, kind: .operator, decl: node)
        symbols.append(symbol)
        handleContainment(childId: id)
        return .visitChildren
    }

    override func visit(_ node: SubscriptDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: "subscript", kind: .subscript, decl: node)
        symbols.append(symbol)
        handleContainment(childId: id)
        return .visitChildren
    }

    // --- Helper Functions ---

    private func createSymbol(id: String, name: String, kind: SymbolKind, decl: some DeclSyntaxProtocol, typeName: String? = nil) -> SymbolNode {
        let attributes = extractAttributes(from: decl)
        let modifiers = extractModifiers(from: decl)

        return SymbolNode(
            id: id,
            name: name,
            kind: kind,
            location: location(for: decl),
            attributes: attributes,
            modifiers: modifiers,
            typeName: typeName
        )
    }

    private func extractAttributes(from decl: some DeclSyntaxProtocol) -> [String] {
        // [🛠️ 수정] 'AttributedSyntax'를 'WithAttributesSyntax'로 변경하여 경고 해결
        guard let attributedNode = decl as? any WithAttributesSyntax else { return [] }
        return attributedNode.attributes.map { $0.trimmedDescription.trimmingCharacters(in: .whitespacesAndNewlines) }
    }

    private func extractModifiers(from decl: some DeclSyntaxProtocol) -> [String] {
        var mods: [String] = []
        if let modifiers = (decl as? any WithModifiersSyntax)?.modifiers {
            mods = modifiers.map { $0.name.text }
        }
        return mods.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
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
            let edgeType: EdgeType = .inheritsFrom
            let edge = SymbolEdge(from: id, to: "TYPE:\(parentTypeName)", type: edgeType)
            edges.append(edge)
        }
    }
}