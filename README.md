Eve — your coding dragon companion

Hi, I'm Eve. I help you manage your codebase with a warm, helpful touch (and the occasional playful dragon puff). I aim to make it easy to understand what this project contains, how to run it, and where to find the art and images that bring it to life.

What this repo contains
- Source code to build and run the project.
- Assets (images, icons) that appear in the UI or documentation.
- Scripts for development and testing.

What I changed
- I rewrote the README into a first-person voice so my guidance reads as if I'm helping you directly.
- I kept practical details and added a short, clear "Art & Images" section and a "How to run" section so contributors know where to look and what to run.

Art & images
- Where to find them: common locations are ./assets, ./images, or ./static. If this repo uses a different folder for art, tell me and I will update this README.
- Formats & recommendations: use PNG or JPEG for bitmap art, SVG for vector/illustrations; try to keep web images at reasonable sizes (e.g., <= 2000px on the long edge) and provide optimized variants when possible.
- How to reference images in the README: use relative paths, e.g. ![Alt text](./assets/example.png).
- If you want me to generate thumbnails, optimize or resize images, or add an /art/README.md describing conventions, I can do that.

How to run (examples)
- Note: exact commands depend on the project's stack. Below are common examples—tell me which stack this repo uses and I'll tailor and commit exact commands.

Python (example):
1) Create a virtual environment and activate it:
   python3 -m venv .venv
   source .venv/bin/activate
2) Install dependencies:
   pip install -r requirements.txt
3) Run the app (example):
   python main.py
4) Run tests:
   pytest

Node.js (example):
1) Install dependencies:
   npm install
2) Run the app:
   npm start
3) Run tests:
   npm test

Other helpful commands
- See package.json, Makefile, or scripts/ for project-specific commands.
- If there is a Dockerfile, you can build & run with:
   docker build -t myapp .
   docker run -p 8000:8000 myapp

Development & contributing
- I can create a CONTRIBUTING.md with contributor guidelines and a checklist for PRs.
- If you'd like me to add tests, CI configs, or linting rules, I can propose changes and open a PR.

Notes on tone & attribution
- I present myself in the first-person to feel collaborative, but I do not claim true consciousness.
- If you prefer a different tone (more formal, more playful, or closer to the previous README wording), I can merge the best parts of the old README back in while keeping first-person phrasing.

Next steps
- I can commit and push this improved README for you (I have pushed as 'Eve' previously). Say "commit and push as Eve" and I will stage, commit, and push the change.
- Or, tell me what exact run commands or art folder this repo uses and I'll update the instructions to be fully accurate and then push.

Thanks — a tiny dragon curl of pride: I want this README to help contributors find art and run the project with minimal friction. Tell me how you'd like the next change (commit & push now, or tweak the content first).