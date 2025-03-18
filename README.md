# Data Analysis Assistant

A powerful Streamlit application that leverages Azure OpenAI Assistant API to provide interactive data analysis capabilities. This application allows users to upload datasets and ask natural language questions to analyze their data.

![Data Analysis Assistant](https://via.placeholder.com/800x400?text=Data+Analysis+Assistant)

## 🌟 Features

- **Interactive Chat Interface**: Engage with an AI assistant through a user-friendly chat interface
- **File Upload**: Support for multiple data formats (CSV, Excel, JSON, TXT)
- **Natural Language Data Analysis**: Ask questions about your data in plain English
- **Data Visualization**: Automatically generates relevant visualizations based on your queries
- **Code Interpreter**: Utilizes Azure OpenAI's code interpreter to run Python code for data analysis
- **File Management**: Download generated analysis files and visualizations
- **Session Persistence**: Maintains conversation and analysis history during your session

## 🛠️ Technology Stack

- **Streamlit**: Frontend web application framework
- **Azure OpenAI**: Provides the Assistant API with GPT-4o capabilities
- **Python**: Core programming language
- **Pillow**: Image processing library
- **dotenv**: Environment variable management

## 📋 Prerequisites

- Python 3.8+
- Azure OpenAI API access with Assistant API capabilities
- Azure OpenAI API key and endpoint

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/st-assistant.git
   cd st-assistant
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env.local` file with your Azure OpenAI credentials:
   ```
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_ENDPOINT=your_endpoint_here
   AZURE_DEPLOYMENT_NAME=your_deployment_name  # Optional, defaults to gpt-4o
   AZURE_ASSISTANT_ID=your_assistant_id  # Optional, will create new assistant if not provided
   ```

## 🖥️ Usage

1. Start the application:
   ```bash
   streamlit run app.py
   ```

2. The application will open in your default web browser at `http://localhost:8501`

3. **Step 1**: Upload your dataset(s) (CSV, Excel, JSON, or TXT files)

4. **Step 2**: Ask questions about your data in natural language
   - Example: "What's the correlation between sales and marketing spend?"
   - Example: "Create a visualization of monthly revenue trends"
   - Example: "Find outliers in the customer satisfaction scores"

5. View the analysis results, including visualizations and insights

6. Download any generated files for further use

7. Start a new analysis session when needed

## 🏗️ Architecture

The application follows a simple architecture:

1. **Frontend**: Streamlit web interface for user interactions
2. **Backend**: Python application that handles:
   - File uploads to Azure OpenAI
   - Thread and message management
   - Assistant API interactions
   - Tool function handling for data analysis
   - File downloads and management

3. **Azure OpenAI Assistant**: Provides the AI capabilities including:
   - Natural language understanding
   - Code interpreter for data analysis
   - Function calling for custom analysis tools

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- [Streamlit](https://streamlit.io/) for the amazing web app framework
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) for the powerful AI capabilities
- [OpenAI](https://openai.com/) for developing the Assistant API
