mod indexer;
mod llm;
use std::thread;
use std::sync;
fn main() {
    let files = indexer::list_files("/home/liyu-zerihun/EVE/src/test_src");
    let mut codebase = indexer::code_base{
    	files: Vec::new(),
    	objects: Vec::new(),
    	morphisms: Vec::new(),
    };

    let num_files = files.len();
    println!("Number of files found: {}", num_files);

    let num_cores = thread::available_parallelism().map(|n| n.get()).unwrap_or(1);
    println!("Number of CPU cores available: {}", num_cores);

    let div : usize = (num_files as f32 / num_cores as f32).ceil() as usize;
    println!("Dividing work into chunks of size: {}", div);

    let mut start = 0;
    let mut handles = vec![];
    let num_indexed = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
    for i in 0..num_cores {
    	let end = if start + div > num_files { num_files } else { start + div };
        let file_chunk = files[start..end].to_vec();
        start = end;
        let mut codebase_clone = codebase.clone();
        let num_indexed = std::sync::Arc::clone(&num_indexed);
        handles.push(thread::spawn(move || {
            for file in &file_chunk {
                //Increment the indexed file count
                num_indexed.fetch_add(1, std::sync::atomic::Ordering::Relaxed);


                let input = std::fs::read_to_string(file).expect("Failed to read file");
                let res = tokio::runtime::Runtime::new().unwrap().block_on(llm::request_llm(input));
                let info_tuple = llm::parse_llm_response(res.unwrap(), file.to_string());
                // Accumulate parsed info into the codebase clone
                codebase_clone.files.push(info_tuple.0);
                codebase_clone.objects.extend(info_tuple.1);
                codebase_clone.morphisms.extend(info_tuple.2);
            }
            codebase_clone
        }));
    }
    // Spawn a thread to monitor progress
    let num_indexed_clone = std::sync::Arc::clone(&num_indexed);
    let progress_handle = thread::spawn(move || {
        loop {
            let count = num_indexed_clone.load(std::sync::atomic::Ordering::Relaxed);
            print!("\rIndexed {}/{} files", count, num_files);
            std::io::Write::flush(&mut std::io::stdout()).unwrap();
            if count >= num_files {
                println!();
                break;
            }
            std::thread::sleep(std::time::Duration::from_secs(2));
        }
    });
    for handle in handles {
        let partial_codebase = handle.join().unwrap();
        codebase.files.extend(partial_codebase.files);
        codebase.objects.extend(partial_codebase.objects);
        codebase.morphisms.extend(partial_codebase.morphisms);
    }
    progress_handle.join().unwrap();

    // Example search usage
    let query : String = "A function that sends requests for autocompletion".to_string();
    let query_type = "morphism";
    let results = indexer::search_codebase(&codebase, query.clone(), query_type);
    if results.relevant_morphisms.len() > 0 {
    	println!("Search Results for query '{}' of type '{}':", query, query_type);
    	for morphism in results.relevant_morphisms {
    		println!("Morphism: {}, Description: {}", morphism.name, morphism.description);
    	}
    } else {
    	println!("No relevant morphisms found for query '{}' of type '{}'.", query, query_type);
    }
}