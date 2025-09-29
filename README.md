# **Gravia: The Advanced Desktop Virtual Assistant 🚀**

**Gravia** is a next-generation desktop virtual assistant designed to give you unparalleled control and efficiency over your computer and digital life. Going beyond simple commands, Gravia uses context-aware intelligence, multimodal understanding, and secure system access to become your personal, all-in-one productivity hub.

[Demo](https://youtu.be/lFxlhrK259M)

## **✨ Key Features**

* **Real-time Data:** Get up-to-the-minute information, from weather and news to stock prices and more.  
* **Deep OS Integration:** Interact with your operating system on a new level. Gravia can open and close applications and websites, and even intelligently capture context from your screen and file explorer to anticipate your needs.  
* **Secure System & Shell Access:** Gravia can safely access your file system and command shell to perform complex, multi-step tasks for you. A built-in, secure Python code interpreter provides endless customization and capability without compromising your security.  
* **Productivity Tools:** Stay organized with smart alarms, timers, and reminders that can be set with simple voice or text commands.  
* **Extensive Service Integrations:** Connect to all your favorite services seamlessly. Gravia supports integrations with:  
  * Gmail, Google Drive, Google Calendar  
  * OneDrive, Notion  
  * Instagram, Facebook, X (Twitter), Reddit, and more\!  
* **Headless Music Playback:** Enjoy your favorite tunes without needing to have a music application visible. Gravia can play songs in the background, freeing up your screen.  
* **Agentic RAG:** Leverage Gravia's powerful Agentic Retrieval-Augmented Generation (RAG) to provide your own custom data, allowing you to create a truly personalized assistant that knows your specific information.  
* **Multimodal Understanding:** Gravia isn't just a voice assistant. It understands and processes **audio, video, images, and text**, allowing for a richer, more natural interaction.  
* **Built-in File Utilities:** Perform common file operations with ease, including converting any file format to any other format, and merging or splitting PDFs.  
* **Natural Voices & ASR:** Communicate naturally with Gravia. It features high-quality, natural voices for text-to-speech (TTS) and an **awesome Automatic Speech Recognition (ASR)** system built with **Deepgram**.  
* **Customizable:** Tailor Gravia to your unique workflow and preferences.  
* **... and more\!** We're constantly adding new features to make Gravia smarter and more powerful.

## **💻 Installation & Setup**

We offer two methods for getting Gravia running, depending on whether you're a standard user or a developer.

### **1\. For Normal Users (Quick Start)**

This is the recommended method for users who want to quickly install and use Gravia with minimal setup.

#### **Prerequisites**

For full functionality, ensure these external dependencies are installed on your system:

* **FFmpeg:** Required for advanced file conversion and manipulation tasks.  
  * [Download FFmpeg](https://ffmpeg.org/download.html)
* **Python:** Required for backend services.  
  * [Download Python](https://www.python.org/downloads/)
* **uv:** A fast dependency manager for Python.  
  * [Download uv](https://docs.astral.sh/uv/getting-started/installation)

#### **Installation**

#### **1\. Backend Setup**

The backend is built with Python, utilizing the FastAPI framework.

1. **Navigate to the Backend Directory:**  
   cd gravia/backend

2. Set Up Environment Variables:  
   Create a .env file in the backend directory and populate it with the necessary API keys for core services.

| Service | Environment Variable(s) | Description |
| :---- | :---- | :---- |
| Core LLM (Gemini) | GOOGLE\_API\_KEY or GEMINI\_API\_KEY | Key for core AI reasoning and intelligence. |
| ASR (Deepgram) | DEEPGRAM\_API\_KEY | Key for high-accuracy Automatic Speech Recognition. |
| Integrations (Composio) | COMPOSIO\_API\_KEY | Key for connecting to various third-party services (Gmail, Notion, etc.). |
| Observability (Langfuse) | LANGFUSE\_PUBLIC\_KEY, LANGFUSE\_SECRET\_KEY | Keys for tracking and analyzing LLM chain execution. |

3. Install Dependencies (using uv):  
   We recommend using uv for fast dependency management.  
   \# Install dependencies listed in pyproject.toml  
   uv pip install \-r pyproject.toml  
   \# OR, for locking and synchronization:  
   uv sync

4. **Run the FastAPI Server:**  
   \# Run the main application file (recommended if using uv run)  
   uv run main.py  
   \# OR, for development with hot-reloading:  
   fastapi dev main.py

#### **2\. Frontend Setup**

1. **Install via installer:**  
   Download and run the installer from our [Releases Page](https://github.com/Naitik4516/Gravia/releases/latest).
   This will set up the frontend application and create a desktop shortcut for easy access.
2. **Run the Frontend Application:**  
   Launch the Gravia application from your desktop shortcut or start menu.

## **⚙️ Upcoming Features & Roadmap**

We're always working to expand Gravia's capabilities. Here’s what you can expect in the near future:

* **Wake Word Detection:** Activate Gravia with a simple voice command, without needing to press a button.  
* **GUI Automation:** Automate tasks within graphical user interfaces, making it possible to control any desktop application.  
* **Autonomous Agents:** We're developing a suite of specialized autonomous agents for tasks like:  
  * **Deep research**  
  * **Complex automation**  
  * **Reasoning**  
  * **Image generation & editing**  
* **Deeper Computer Integration:** We aim to integrate Gravia even more profoundly with your computer, allowing for a level of control and efficiency that has never been seen before.  
* **More Integrations:** More services and platforms will be supported to make Gravia the ultimate universal assistant.

## **🤝 Contributing**

We welcome contributions from the community\! If you're interested in helping us build the future of virtual assistants, please check out our CONTRIBUTING.md file for guidelines on how to get started.

## **📜 License**

Gravia is released under the **AGPL-3.0 License**. See the LICENSE file for more details.