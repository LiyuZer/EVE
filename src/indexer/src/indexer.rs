use crate::llm;
use std::fmt;
// This is the rust code for the indexer module. We simply loop through all the files and canonicalize them
#[derive(Default, Debug, Clone)]
pub struct code_base {
	pub files: Vec<llm::File>,
	pub objects: Vec<llm::Object>,
	pub morphisms: Vec<llm::Morphism>,
}
#[derive(Default, Debug, Clone)]
pub struct query_result {
	pub relevant_files: Vec<llm::File>,
	pub relevant_objects: Vec<llm::Object>,
	pub relevant_morphisms: Vec<llm::Morphism>,
}

// A function that will loop through all the files in a root directory
pub fn list_files(root_dir : &str) -> Vec<String> {
	let paths = std::fs::read_dir(root_dir).unwrap();
    // Create a stack vector to hold directories to visit
    let mut stack : Vec<String> = Vec::new();
	let mut files : Vec<String> = Vec::new();
	
    stack.push(root_dir.to_owned());
	while stack.len() > 0 {
		let current_dir = stack.pop().unwrap();
		let paths = std::fs::read_dir(current_dir).unwrap();
	
		for path in paths {
			let path = path.unwrap().path();
			if path.is_file() {
				// Process file
				let path_str = path.to_str().unwrap().to_owned();
				files.push(path_str);
			}
			if path.is_dir() {
				let path_str = path.to_str().unwrap().to_owned();
				stack.push(path_str);
			}		
		}
	}
	return files;
}


pub fn cosine_similarity(vec1: &Vec<f32>, vec2: &Vec<f32>) -> f32 {
	let dot_product: f32 = vec1.iter().zip(vec2.iter()).map(|(a, b)| a * b).sum();
	let magnitude1: f32 = vec1.iter().map(|x| x * x).sum::<f32>().sqrt();
	let magnitude2: f32 = vec2.iter().map(|x| x * x).sum::<f32>().sqrt();
	if magnitude1 == 0.0 || magnitude2 == 0.0 {
		return 0.0;
	}
	dot_product / (magnitude1 * magnitude2)
}
// A function given some query, with a query type will search the code base for relevant information
pub fn search_codebase(code_base: &code_base, query: String, query_type: &str) -> query_result {
	// For now we will return an empty query result
	// A quick vector search based on embeddings 
	let query_vec:Result<Vec<f32>, Box<dyn std::error::Error>> = tokio::runtime::Runtime::new().unwrap().block_on(llm::get_embeddings(query.clone()));
	if query_vec.is_err() {
		return query_result {
			relevant_files: Vec::new(),
			relevant_objects: Vec::new(),
			relevant_morphisms: Vec::new(),
		};
	}
	let query_vec = query_vec.unwrap();
	//Now that we have the vector we can search the code base
	if query_type == "file" {
		let mut relevant_files = Vec::new();
		let mut file_similarities = Vec::new();
		for file in code_base.files.iter() {
			// Compute similarity between query and file embedding as a simple heuristic
			let file_vec = file.embedding.clone();
			let similarity = cosine_similarity(&query_vec, &file_vec);
			relevant_files.push((*file).clone());
			file_similarities.push(similarity);
			println!("Similarity between query and file {}: {}", file.path, similarity);
		}
		//Sort relevant files by similarity descending by similarity
		let mut combined: Vec<(llm::File, f32)> = relevant_files.into_iter().zip(file_similarities.into_iter()).collect();
		combined.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
		let relevant_files: Vec<llm::File> = combined.into_iter().map(|(file, _)| file).collect();
		return query_result {
			relevant_files,
			relevant_objects: Vec::new(),
			relevant_morphisms: Vec::new(),
		};
	} else if query_type == "object" {
		// Search for objects
		let mut relevant_objects = Vec::new();
		let mut object_similarities = Vec::new();
		for obj in code_base.objects.iter() {
			let obj_vec = obj.embedding.clone();
			let similarity = cosine_similarity(&query_vec, &obj_vec);
			object_similarities.push(similarity);
			relevant_objects.push(obj.clone());
		}
		// Sort relevant objects by similarity descending
		let mut combined: Vec<(llm::Object, f32)> = relevant_objects.into_iter().zip(object_similarities.into_iter()).collect();
		combined.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
		let relevant_objects: Vec<llm::Object> = combined.into_iter().map(|(obj, _)| obj).collect();
		return query_result {
			relevant_files: Vec::new(),
			relevant_objects,
			relevant_morphisms: Vec::new(),
		};
	}
	 else if query_type == "morphism" {
		// Search for morphisms
		let mut relevant_morphisms = Vec::new();
		let mut morphism_similarities = Vec::new();
		for morph in code_base.morphisms.iter() {
			let morph_vec = morph.embedding.clone();
			let similarity = cosine_similarity(&query_vec, &morph_vec);
			morphism_similarities.push(similarity);
			relevant_morphisms.push(morph.clone());
		}
		// Sort relevant morphisms by similarity descending
		let mut combined: Vec<(llm::Morphism, f32)> = relevant_morphisms.into_iter().zip(morphism_similarities.into_iter()).collect();
		combined.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
		let relevant_morphisms: Vec<llm::Morphism> = combined.into_iter().map(|(morph, _)| morph).collect();
		return query_result {
			relevant_files: Vec::new(),
			relevant_objects: Vec::new(),
			relevant_morphisms,
		};
	}
	return query_result {
		relevant_files: Vec::new(),
		relevant_objects: Vec::new(),
		relevant_morphisms: Vec::new(),
	};
}