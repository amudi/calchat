# CalChat - Cal.com Calendar Assistant

CalChat is an AI-powered chat interface for managing Cal.com calendars. It allows users to book, view, reschedule, and cancel meetings through a natural language conversation.

## Features

- **Book new meetings**: Schedule appointments with specific event types
- **View scheduled events**: List upcoming or past meetings filtered by various criteria
- **Cancel meetings**: Cancel single or recurring meetings
- **Reschedule meetings**: Move meetings to new time slots
- **View event types**: Get information about available meeting types

## Technical Stack

- **Python 3.9+**
- **LangChain**: For AI agent and tool orchestration
- **FastAPI**: For the API server and WebSockets
- **Chainlit**: For the chat UI
- **OpenAI API**: For LLM capabilities
- **Cal.com API v2**: For calendar management

## Setup

### Prerequisites

- Python 3.9 or higher
- Poetry (Python package manager)
- Cal.com API key
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/calchat.git
   cd calchat
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   Create a `.env` file in the `app` directory with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4o-mini
   CAL_DOT_COM_API_KEY=your_cal_dot_com_api_key
   CAL_DOT_COM_USERNAME=your_cal_username
   CHAINLIT_AUTH_SECRET=your_chainlit_auth_secret
   ```
   You can run
   ```bash
   poetry run chainlit create-secret
   ```
   to generate `CHAINLIT_AUTH_SECRET`

### Running the Application

1. Activate the Poetry environment:
   ```bash
   poetry shell
   ```

2. Start the FastAPI server:
   ```bash
   python -m app.main
   ```

4. Visit `http://localhost:8080/chainlit` in your browser to interact with the assistant. Login with any email / password since the app mocks out authentication.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For support, please open an issue on the GitHub repository or contact the maintainer at your-email@example.com.
