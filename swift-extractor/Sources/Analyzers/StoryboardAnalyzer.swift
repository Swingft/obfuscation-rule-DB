import Foundation

class StoryboardAnalyzer: NSObject, XMLParserDelegate {
    private let fileManager = FileManager.default
    private var foundClasses = Set<String>()

    func analyze(projectURL: URL) -> [String: URL] {
        var references = [String: URL]()
        let enumerator = fileManager.enumerator(at: projectURL, includingPropertiesForKeys: nil, options: [.skipsHiddenFiles])

        while let fileURL = enumerator?.nextObject() as? URL {
            if ["storyboard", "xib"].contains(fileURL.pathExtension) {
                if let parser = XMLParser(contentsOf: fileURL) {
                    parser.delegate = self
                    foundClasses.removeAll()
                    parser.parse()
                    for className in foundClasses {
                        references[className] = fileURL
                    }
                }
            }
        }
        return references
    }

    // XMLParserDelegate 메서드
    func parser(_ parser: XMLParser, didStartElement elementName: String, namespaceURI: String?, qualifiedName qName: String?, attributes attributeDict: [String : String] = [:]) {
        if let customClass = attributeDict["customClass"] {
            foundClasses.insert(customClass)
        }
    }
}