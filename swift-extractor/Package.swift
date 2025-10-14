// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SymbolExtractor",
    platforms: [.macOS(.v12)],
    dependencies: [
        .package(url: "https://github.com/apple/swift-syntax.git", from: "510.0.0"),
        .package(url: "https://github.com/apple/swift-argument-parser.git", from: "1.2.0"),
    ],
    targets: [
        .executableTarget(
            name: "SymbolExtractor",
            dependencies: [
                .product(name: "SwiftSyntax", package: "swift-syntax"),
                .product(name: "SwiftParser", package: "swift-syntax"),
                .product(name: "ArgumentParser", package: "swift-argument-parser")
            ],
            // Sources 디렉토리 하위의 경로를 명시해줍니다.
            path: "Sources"
        ),
    ]
)