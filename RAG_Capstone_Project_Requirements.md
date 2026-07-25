# Capstone Project: Retrieval-Augmented Generation (RAG)

## Project Overview

For the final course project, students must implement a **multimodal Retrieval-Augmented Generation (RAG) pipeline**.

In this project, **multimodal** means that the system should be able to search, retrieve, and use information from different content sources, including:

- PDF documents
- Images

> Video files are not required as an input source.

A starter RAG project that already supports PDF files is provided here:

[Starter Repository: RAGPDFTeachingDemo](https://github.com/fatimarajab12/RAGPDFTeachingDemo)

---

## Team Requirements

- Each team must consist of **2 or 3 students**.
- Individual submissions are not allowed unless approved by the instructor.

---

## Technical Requirements

The project should:

- Implement a functional RAG pipeline.
- Support retrieval from PDF files.
- Extend the provided system to support multimodal content, especially images.
- Correctly retrieve relevant information.
- Generate answers based on the retrieved content.
- Be complete, functional, and ready for demonstration.

---

## GitHub Requirements

Each team must:

1. Create or use a GitHub repository for the project.
2. Upload all project source code to the repository.
3. Add the instructor as a collaborator or contributor.
4. Preferably give the instructor administrator access.

Instructor contact provided in class:

- Email: `sam.hamed@gmail.com`

> Use the instructor's GitHub username provided during the course when sending the repository invitation.

---

## Local Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/fatimarajab12/RAGPDFTeachingDemo.git
```

### 2. Open the Project Folder

Example location on Windows:

```text
C:\Users\<username>\Documents\Dev\GitHub
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

### 4. Activate the Virtual Environment

#### Windows

```bash
venv\Scripts\activate
```

#### macOS or Linux

```bash
source venv/bin/activate
```

### 5. Install the Dependencies

Run the following command inside the activated virtual environment:

```bash
pip install -r requirements.txt
```

### 6. Configure the API Key

Obtain an API key from one of the following:

- OpenAI Platform
- OpenRouter

Add the API key to the project's `.env` file.

Example:

```env
API_KEY=your_api_key_here
```

> Use the exact environment-variable name expected by the starter project.

### 7. Start the Backend

Run the backend using the command specified in the starter repository documentation.

### 8. Start the Frontend

Run the frontend using the command specified in the starter repository documentation.

---

## Project Demonstration Video

Each team must record a video that:

- Explains the project clearly.
- Demonstrates how the system works.
- Shows the main features and functionality.
- Includes all team members.
- Does not exceed **15 minutes**.

Every team member should appear and participate in the video.

---

## Submission Requirements

Before submitting, confirm that your team has completed the following:

- [ ] The team consists of 2 or 3 students.
- [ ] The multimodal RAG pipeline is functional.
- [ ] PDF retrieval works correctly.
- [ ] Image or multimodal retrieval has been implemented.
- [ ] The complete source code is uploaded to GitHub.
- [ ] The instructor has been added to the GitHub repository.
- [ ] The API key is stored securely in a `.env` file.
- [ ] The `.env` file is excluded from GitHub using `.gitignore`.
- [ ] The backend runs successfully.
- [ ] The frontend runs successfully.
- [ ] All team members appear in the demonstration video.
- [ ] The video is no longer than 15 minutes.

---

## Evaluation

The project is worth **30 points**.

Projects will be evaluated mainly based on:

- Correctness
- Functionality
- Successful implementation of the RAG pipeline
- Multimodal support
- Quality of the project demonstration
