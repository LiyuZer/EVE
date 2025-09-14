// We will interact with an LLM using the openAI endpoint. 
use reqwest;
use reqwest::header::{ACCEPT, AUTHORIZATION, CONTENT_TYPE};
use tokio;
use serde_json;
use std::fmt;
#[derive(Debug, Clone, Default)]
pub struct File{
    pub size: u64,
    pub name: String,
    pub path: String,
    pub language: String,
    pub description: String,
    pub embedding: Vec<f32>,
}
impl fmt::Display for File {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "File(name: {}, path: {}, language: {}, description: {})", self.name, self.path, self.language, self.description)
    }
}
#[derive(Debug, Clone, Default)]
pub struct Object {
    pub name: String,
    pub obj_type: String,
    pub morphisms: Vec<String>,
    pub dependencies: Vec<String>,
    pub description: String,
    pub embedding: Vec<f32>,
}
impl fmt::Display for Object {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Object(name: {}, type: {}, morphisms: {:?}, dependencies: {}, description: {})",
            self.name,
            self.obj_type,
            self.morphisms,
            self.dependencies.join(", "),
            self.description
        )
    }
}
#[derive(Debug, Clone, Default)]
pub struct Morphism {
    pub name: String,
    pub morph_type: String,
    pub dependencies: Vec<String>,
    pub description: String,
    pub embedding: Vec<f32>,
}
impl fmt::Display for Morphism {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Morphism(name: {}, type: {}, dependencies: {}, description: {})",
            self.name,
            self.morph_type,
            self.dependencies.join(", "),
            self.description
        )
    }
}

pub async fn request_llm(input : String) -> Result<String, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let api_key = "sk-REDACTED";
    let response = "https://api.openai.com/v1/responses";
    let base_prompt = r#"You are a code canonicalizer, you will receive code snippets and you wil output the canonicalized version of the code. Return a json of object, function relationships
    Objects are classes, structs, interfaces, not imports. Morphisms are functions, methods, procedures. You will identify the objects and morphisms in the code and their relationships.
    Note only add to objects and functions that are explicitly defined in the code. Do not add any extra objects or functions.
    Add dependencies to objects and functions. Dependencies are other objects or functions that are used or called by the object or function, they don't
    have to be defined in the code snippet. Descriptions are medium length, but extremely informative, distinct and focused on the semantic and purpose-related details of the objects and morphisms.
    An example 
        import json
        import requests
        class Animal:
            def __init__(self, name):
                self.name = name

            def speak(self):
                raise NotImplementedError('Subclasses must implement this method.')
        class Dog(Animal):
            def speak(self):

                return f'{self.name} says Woof!'
            def fetch_inst(url):
                response = requests.get(url)
                if response.status_code == 200:
                    return response.json()
                else:
                    response.raise_for_status()

        # You will return 
        {
            'General Information': {
                'Total Objects': 2,
                'Total Morphisms': 3,
                'Language': 'Python',
                'Description': 'This code defines a base class Animal with an abstract method speak, and a subclass Dog that implements the speak method, the dog days woof. It also includes a function fetch_inst for fetching JSON data from a URL.'
            },
            'Objects':
            [
                {"name": "Animal", "type": "class", "morphisms": ["__init__", "speak"], "Dependencies": [], "description": "Base python class for animals with a speak method that must be implemented by subclasses."},
                {"name": "Dog", "type": "class", "morphisms": ["speak"], "Dependencies": ["Animal"], "description": "Dog class inheriting from Animal, implements the speak method to return a dog-specific sound."},
            ]
            
            'Morphisms':
            [
                {"name": "__init__", "type": "method", "Dependencies": ["self", "name"], "description": "Initializes the Animal class with a name attribute."},
                {"name": "speak", "type": "method", "Dependencies": ["self"], "description": "Abstract method in Animal class, must be overridden in subclasses to provide specific animal sounds."},
                {"name": "fetch_inst", "type": "function", "Dependencies": ["url"], "description": "Fetches JSON data from a given URL using HTTP GET request."}
            ]

        
        }
            Input :
            "#;
    let input = format!("{}{}", base_prompt, input);
    let body = serde_json::json!({
        "model": "gpt-4.1-mini",
        "input" : input
    });
    let res = client.post(response)
        .header(AUTHORIZATION, format!("Bearer {}", api_key))
        .header(CONTENT_TYPE, "application/json")
        .header(ACCEPT, "application/json")
        .json(&body)
        .send()
        .await?;

    if !res.status().is_success() {
        return Err(format!("Request failed with status: {}", res.status()).into());
    }
    else {
        // println!("Request succeeded with status: {}", res.status());
    }
    let res_text = res.text().await?;
    // Convert the response to a JSON object
    let res_json: serde_json::Value = serde_json::from_str(&res_text)?;
    // println!("Response JSON: {}", res_json);
    // Extract the message field from the JSON object
    let message = res_json.get("output");
    if message.is_none() {
        return Err("No message field in response".into());
    }
    let message = message.unwrap();
    let text =  message[0]["content"][0]["text"].clone();
    let text = text.as_str().unwrap().to_string();
    // Extract only json from the text
    let start = text.find('{').ok_or("No JSON found in response")?;
    let end = text.rfind('}').ok_or("No JSON found in response")?;
    let text = &text[start..=end];
    let text = text.to_string();
    Ok(text)

}


// Function that outputs embeddings for a given text using openAI embeddings endpoint
pub async fn get_embeddings(text: String) -> Result<Vec<f32>, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let api_key = "sk-REDACTED";
    let response = "https://api.openai.com/v1/embeddings";
    let body = serde_json::json!({
        "model": "text-embedding-3-large",
        "input" : text
    });
    let res = client.post(response)
        .header(AUTHORIZATION, format!("Bearer {}", api_key))
        .header(CONTENT_TYPE, "application/json")
        .json(&body)
        .send()
        .await?
        .json::<serde_json::Value>()
        .await?;

    let embeddings = res["data"][0]["embedding"]
        .as_array()
        .ok_or("No embedding found")?
        .iter()
        .filter_map(|v| v.as_f64().map(|f| f as f32))
        .collect();

    Ok(embeddings)
}


// Function that takes in raw llm response and parses it into File, Object and Morphism structs
pub fn parse_llm_response(response: String, file_path: String) -> (File, Vec<Object>, Vec<Morphism>) {
    // Extract File Name 
    let file_name = std::path::Path::new(&file_path)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("")
        .to_string();

    
    // Parse the output string as JSON
    let parsed: serde_json::Value = serde_json::from_str(&response).expect("Failed to parse JSON");
    // Extract general information
    let general_info = &parsed["General Information"];
    let language = general_info["Language"].as_str().unwrap_or("").to_string();
    let description = general_info["Description"].as_str().unwrap_or("").to_string();
    // Get embedding for description
    let description_clone = description.clone();
    let embeddings = get_embeddings(description_clone);
    let description_embedding = tokio::runtime::Runtime::new().unwrap().block_on(embeddings).unwrap_or_else(|_| vec![]);
    // Create File struct
    let file = File {
        size: 0, // Size can be set later
        name: file_name,
        path: file_path,
        language,
        embedding: description_embedding,
        description,

    };

    // Extract Objects
    let mut objects = Vec::new();
    if let Some(objs) = parsed.get("Objects").and_then(|v| v.as_array()) {
        for obj in objs {
            let name = obj.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let obj_type = obj.get("type").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let morphisms = obj.get("morphisms")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|m| m.as_str().map(|s| s.to_string())).collect())
                .unwrap_or_else(Vec::new);
            let dependencies = obj.get("Dependencies")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|d| d.as_str().map(|s| s.to_string())).collect())
                .unwrap_or_else(Vec::new);
            let description = obj.get("description").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let embeddings = get_embeddings(description.clone());
            let embeddings = tokio::runtime::Runtime::new().unwrap().block_on(embeddings).unwrap_or_else(|_| vec![]);

            objects.push(Object {
                name,
                obj_type,
                morphisms,
                dependencies,
                embedding: embeddings,
                description,
            });
        }
    }

    // Extract Morphisms
    let mut morphisms = Vec::new();
    if let Some(morphs) = parsed.get("Morphisms").and_then(|v| v.as_array()) {
        for morph in morphs {
            let name = morph.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let morph_type = morph.get("type").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let dependencies = morph.get("Dependencies")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|d| d.as_str().map(|s| s.to_string())).collect())
                .unwrap_or_else(Vec::new);
            let description = morph.get("description").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let embeddings = get_embeddings(description.clone());
            let embeddings = tokio::runtime::Runtime::new().unwrap().block_on(embeddings).unwrap_or_else(|_| vec![]);
            morphisms.push(Morphism {
                name,
                morph_type,
                dependencies,
                embedding: embeddings,
                description,
            });
        }
    }

    (file, objects, morphisms)
}

