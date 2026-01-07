import Foundation
import FoundationModels

// MARK: - Errors

enum GenerateError: LocalizedError {
    case modelNotAvailable
    case generationFailed(String)
    case invalidSchema(String)
    case missingPrompt

    var errorDescription: String? {
        switch self {
        case .modelNotAvailable: return "Foundation Models not available on this device"
        case .generationFailed(let msg): return "Generation failed: \(msg)"
        case .invalidSchema(let msg): return "Invalid schema: \(msg)"
        case .missingPrompt: return "No prompt provided"
        }
    }
}

// MARK: - JSON Schema Parser

/// Converts a standard JSON Schema dictionary to DynamicGenerationSchema.
/// Supports: object, array, string, number, integer, boolean, enum.
func parseJSONSchema(_ json: [String: Any], name: String = "Root") throws -> DynamicGenerationSchema {
    // Check for anyOf (polymorphism)
    if let anyOf = json["anyOf"] as? [[String: Any]] {
        var schemas: [DynamicGenerationSchema] = []
        for (index, schemaFunc) in anyOf.enumerated() {
            // Try to derive a meaningful name from the nested schema if possible
            var subName = "\(name)_Option\(index)"
            if let properties = schemaFunc["properties"] as? [String: Any],
               let funcObj = properties["function"] as? [String: Any],
               let constName = funcObj["const"] as? String {
                subName = constName
            }
            try schemas.append(parseJSONSchema(schemaFunc, name: subName))
        }
        return DynamicGenerationSchema(name: name, description: json["description"] as? String, anyOf: schemas)
    }

    // Check for enum (simple string union)
    if let enumValues = json["enum"] as? [String] {
        return DynamicGenerationSchema(name: name, description: json["description"] as? String, anyOf: enumValues)
    }
    
    // Check for const (single value enum)
    if let constVal = json["const"] as? String {
        return DynamicGenerationSchema(name: name, description: json["description"] as? String, anyOf: [constVal])
    }

    guard let type = json["type"] as? String else {
        throw GenerateError.invalidSchema("Missing 'type', 'anyOf', 'enum', or 'const' field in schema")
    }

    switch type {
    case "object":
        guard let properties = json["properties"] as? [String: [String: Any]] else {
            throw GenerateError.invalidSchema("Object schema requires 'properties'")
        }
        var schemaProperties: [DynamicGenerationSchema.Property] = []
        for (propName, propSchema) in properties {
            let propDynSchema = try parseJSONSchema(propSchema, name: propName)
            let isOptional = !((json["required"] as? [String])?.contains(propName) ?? false)
            schemaProperties.append(DynamicGenerationSchema.Property(
                name: propName,
                schema: propDynSchema,
                isOptional: isOptional
            ))
        }
        return DynamicGenerationSchema(name: name, description: json["description"] as? String, properties: schemaProperties)

    case "array":
        guard let items = json["items"] as? [String: Any] else {
            throw GenerateError.invalidSchema("Array schema requires 'items'")
        }
        let itemSchema = try parseJSONSchema(items, name: "\(name)Item")
        return DynamicGenerationSchema(
            arrayOf: itemSchema,
            minimumElements: json["minItems"] as? Int,
            maximumElements: json["maxItems"] as? Int
        )

    case "string":
        // Handle const as a single-value enum if present (common in tool definitions)
        if let constVal = json["const"] as? String {
            return DynamicGenerationSchema(name: name, description: json["description"] as? String, anyOf: [constVal])
        }
        return DynamicGenerationSchema(type: String.self, guides: [])

    case "number":
        return DynamicGenerationSchema(type: Double.self, guides: [])

    case "integer":
        return DynamicGenerationSchema(type: Int.self, guides: [])

    case "boolean":
        return DynamicGenerationSchema(type: Bool.self, guides: [])

    default:
        throw GenerateError.invalidSchema("Unsupported type: \(type)")
    }
}

// MARK: - Main

@main
struct GenerateCLI {
    static func main() async {
        let args = CommandLine.arguments

        // Parse arguments
        var prompt: String?
        var temperature: Double?
        var maxTokens: Int?
        var schemaJSON: String?
        
        // Phase 1: New parameters
        var systemPrompt: String?
        var samplingMode: String? // "greedy", "top-k", "top-p"
        var topK: Int?
        var topP: Double?
        var seed: UInt64? // Seed for random sampling
        var modelName: String? // "default", "content-tagging"
        var guardrailsMode: String? // "default", "permissive"

        var i = 1
        while i < args.count {
            switch args[i] {
            case "--temperature":
                i += 1
                if i < args.count { temperature = Double(args[i]) }
            case "--max-tokens":
                i += 1
                if i < args.count { maxTokens = Int(args[i]) }
            case "--json-schema":
                i += 1
                if i < args.count {
                    // Check if it's a file path or inline JSON
                    let schemaArg = args[i]
                    if FileManager.default.fileExists(atPath: schemaArg) {
                        schemaJSON = try? String(contentsOfFile: schemaArg, encoding: .utf8)
                    } else {
                        schemaJSON = schemaArg
                    }
                }
            case "--system-prompt", "--instructions":
                i += 1
                if i < args.count { systemPrompt = args[i] }
            case "--sampling":
                i += 1
                if i < args.count { samplingMode = args[i] }
            case "--top-k":
                i += 1
                if i < args.count { topK = Int(args[i]) }
            case "--top-p":
                i += 1
                if i < args.count { topP = Double(args[i]) }
            case "--seed":
                i += 1
                if i < args.count { seed = UInt64(args[i]) }
            case "--model", "--use-case":
                i += 1
                if i < args.count { modelName = args[i] }
            case "--guardrails":
                i += 1
                if i < args.count { guardrailsMode = args[i] }
            default:
                if prompt == nil {
                    prompt = args[i]
                }
            }
            i += 1
        }

        guard let userPrompt = prompt else {
            fputs("""
                Usage: generate <prompt> [options]
                Options:
                  --temperature <double>           Control randomness (0.0-2.0)
                  --max-tokens <int>              Maximum response tokens
                  --json-schema <path_or_json>    JSON Schema for structured output
                  --system-prompt <string>        System instructions (alias: --instructions)
                  --sampling <mode>               Sampling mode: greedy, top-k, top-p
                  --top-k <int>                   Top-K sampling (default: 40)
                  --top-p <double>                Nucleus sampling (default: 0.9)
                  --seed <int>                    Random seed for reproducibility
                  --model <name>                  Model: default, content-tagging (alias: --use-case)
                  --guardrails <mode>             Guardrails: default, permissive
                
                """, stderr)
            exit(1)
        }

        do {
            // Build the model with use case and guardrails
            let useCase: SystemLanguageModel.UseCase = 
                modelName == "content-tagging" ? .contentTagging : .general
            let guardrails: SystemLanguageModel.Guardrails = 
                guardrailsMode == "permissive" ? .permissiveContentTransformations : .default
            let model = SystemLanguageModel(useCase: useCase, guardrails: guardrails)
            
            // Check availability
            guard await model.availability == .available else {
                throw GenerateError.modelNotAvailable
            }
            
            // Create session with optional instructions
            let session: LanguageModelSession
            if let instructions = systemPrompt {
                session = LanguageModelSession(model: model, instructions: instructions)
            } else {
                session = LanguageModelSession(model: model)
            }
            
            // Build generation options with sampling mode
            var options = GenerationOptions()
            
            // Set sampling mode
            var sampling: GenerationOptions.SamplingMode = .greedy // default
            if let mode = samplingMode {
                switch mode {
                case "greedy":
                    sampling = .greedy
                case "top-k":
                    let k = topK ?? 40
                    if let s = seed {
                        sampling = .random(top: k, seed: s)
                    } else {
                        sampling = .random(top: k, seed: nil)
                    }
                case "top-p":
                    let p = topP ?? 0.9
                    if let s = seed {
                        sampling = .random(probabilityThreshold: p, seed: s)
                    } else {
                        sampling = .random(probabilityThreshold: p, seed: nil)
                    }
                default:
                    fputs("Warning: Unknown sampling mode '\(mode)', using greedy\n", stderr)
                }
            }
            
            // Build full options
            if let temp = temperature, let max = maxTokens {
                options = GenerationOptions(sampling: sampling, temperature: temp, maximumResponseTokens: max)
            } else if let temp = temperature {
                options = GenerationOptions(sampling: sampling, temperature: temp)
            } else if let max = maxTokens {
                options = GenerationOptions(sampling: sampling, temperature: options.temperature, maximumResponseTokens: max)
            } else {
                options = GenerationOptions(sampling: sampling, temperature: options.temperature)
            }
            
            // Generate response
            let result: String
            if let schemaStr = schemaJSON {
                guard let data = schemaStr.data(using: .utf8),
                      let jsonDict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                    throw GenerateError.invalidSchema("Could not parse JSON schema")
                }
                
                let dynamicSchema = try parseJSONSchema(jsonDict)
                let schema = try GenerationSchema(root: dynamicSchema, dependencies: [])
                
                let response = try await session.respond(to: userPrompt, schema: schema, options: options)
                result = response.content.debugDescription
            } else {
                let response = try await session.respond(to: userPrompt, options: options)
                result = response.content
            }
            
            print(result)
        } catch {
            fputs("Error: \(error.localizedDescription)\n", stderr)
            exit(1)
        }
    }
}
