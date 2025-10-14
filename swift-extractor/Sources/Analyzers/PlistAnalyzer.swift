import Foundation

class PlistAnalyzer {
    private let fileManager = FileManager.default
    // Info.plist에서 찾을 클래스 이름 관련 키 목록
    private let principalClassKeys = [
        "NSPrincipalClass", "NSExtensionPrincipalClass", "UISceneDelegateClassName"
    ]

    func analyze(projectURL: URL) -> [String: URL] {
        var references = [String: URL]()
        let enumerator = fileManager.enumerator(at: projectURL, includingPropertiesForKeys: nil, options: [.skipsHiddenFiles])

        while let fileURL = enumerator?.nextObject() as? URL {
            if fileURL.pathExtension == "plist" {
                guard let plistDict = NSDictionary(contentsOf: fileURL) as? [String: Any] else { continue }

                // 1. 최상위 레벨에서 키 찾기
                for key in principalClassKeys {
                    if let className = plistDict[key] as? String {
                        references[className] = fileURL
                    }
                }

                // 2. 중첩된 딕셔너리 내부에서 키 찾기 (e.g., UIApplicationSceneManifest)
                if let sceneManifest = plistDict["UIApplicationSceneManifest"] as? [String: Any],
                   let sceneConfigs = sceneManifest["UISceneConfigurations"] as? [String: Any] {
                    for (_, configValue) in sceneConfigs {
                        if let configDict = configValue as? [[String: Any]] {
                            for item in configDict {
                                if let delegateClassName = item["UISceneDelegateClassName"] as? String {
                                    references[delegateClassName] = fileURL
                                }
                            }
                        }
                    }
                }
            }
        }
        return references
    }
}