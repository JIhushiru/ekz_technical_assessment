# Technical Assessment API
This guide outlines how to set up and run the API locally for the technical assessment.


## Requirements
- **Python Version**: `>=3.10, <3.11` (developed on `3.10.7`)
- **Dependencies**: Listed in `requirements.txt`
---

## Setup
1. **Clone the repository**
    ```bash
    git clone git@github.com:ekz-eric/ekz_technical_assessment.git
    cd ekz_technical_assessment
    ````
2. **Create a venv**
    ```bash
    python -m venv venv
    ```
3. **Activate venv**
   * On **Windows**:
       ```bash
       venv\Scripts\activate
       ```
   * On **macOS/Linux**:
       ```bash
       source venv/bin/activate
       ```
4. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
5. **Create a `.env` file in the `api` directory**

   This file is used to store environment variables needed by the app. For this assessment, add the following line:
   ```env
   API_KEY="abCd3fGh!"
   ```
---

## Running the API locally
Run the API with:
```bash
  python -m api
```
This will start the server locally at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

---

## Using the API
You can view and interact with the API via Swagger UI at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
