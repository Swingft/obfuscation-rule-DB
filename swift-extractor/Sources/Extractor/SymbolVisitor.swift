import SwiftSyntax
import SwiftParser  // 👈 이 import 추가!
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

    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind {
        let id = UUID().uuidString
        let symbol = createSymbol(id: id, name: node.name.text, kind: .method, decl: node)
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
                let symbol = createSymbol(id: id, name: pattern.identifier.text, kind: .property, decl: node)
                symbols.append(symbol)
                handleContainment(childId: id)
            }
        }
        return .visitChildren
    }

    // --- Helper Functions ---

    private func createSymbol(id: String, name: String, kind: SymbolKind, decl: some DeclSyntaxProtocol) -> SymbolNode {
        // attributes와 modifiers를 안전하게 추출
        let attributes = extractAttributes(from: decl)
        let modifiers = extractModifiers(from: decl)

        return SymbolNode(
            id: id,
            name: name,
            kind: kind,
            location: location(for: decl),
            attributes: attributes,
            modifiers: modifiers
        )
    }

    private func extractAttributes(from decl: some DeclSyntaxProtocol) -> [String] {
        // DeclSyntaxProtocol은 attributes를 직접 제공하지 않으므로
        // 구체 타입별로 처리
        var attrs: [String] = []

        if let classDecl = decl.as(ClassDeclSyntax.self) {
            attrs = classDecl.attributes.map { $0.trimmedDescription }
        } else if let structDecl = decl.as(StructDeclSyntax.self) {
            attrs = structDecl.attributes.map { $0.trimmedDescription }
        } else if let enumDecl = decl.as(EnumDeclSyntax.self) {
            attrs = enumDecl.attributes.map { $0.trimmedDescription }
        } else if let funcDecl = decl.as(FunctionDeclSyntax.self) {
            attrs = funcDecl.attributes.map { $0.trimmedDescription }
        } else if let varDecl = decl.as(VariableDeclSyntax.self) {
            attrs = varDecl.attributes.map { $0.trimmedDescription }
        }

        return attrs.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
    }

    private func extractModifiers(from decl: some DeclSyntaxProtocol) -> [String] {
        var mods: [String] = []

        if let classDecl = decl.as(ClassDeclSyntax.self) {
            mods = classDecl.modifiers.map { $0.name.text }
        } else if let structDecl = decl.as(StructDeclSyntax.self) {
            mods = structDecl.modifiers.map { $0.name.text }
        } else if let enumDecl = decl.as(EnumDeclSyntax.self) {
            mods = enumDecl.modifiers.map { $0.name.text }
        } else if let funcDecl = decl.as(FunctionDeclSyntax.self) {
            mods = funcDecl.modifiers.map { $0.name.text }
        } else if let varDecl = decl.as(VariableDeclSyntax.self) {
            mods = varDecl.modifiers.map { $0.name.text }
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
            let edge = SymbolEdge(from: id, to: "TYPE:\(parentTypeName)", type: .inheritsFrom)
            edges.append(edge)
        }
    }
}