# Burmese AI Chatbot

A conversational AI chatbot designed to understand and respond in Burmese language, leveraging Google Vertex AI's Gemini 2.0 Flash models. This chatbot specializes in general questions as well as telecom-specific queries, providing accurate and helpful responses for Ooredoo Myanmar customers.

---

## Features

- **Burmese Language Support:** Natural language understanding and generation in Burmese.
- **Telecom Domain Expertise:** Fine-tuned model for telecom-related questions.
- **General Knowledge:** Utilizes a large language model for general queries.
- **Cloud-based:** Hosted on Google Cloud Platform with Vertex AI and Cloud Storage.
- **No Continuous Deployment Required:** Models are invoked via API calls on-demand.
- **Scalable and Cost-Efficient:** Uses managed services and on-demand endpoints.

---

## Architecture Overview

- **Vertex AI Gemini 2.0 Flash:** Base LLM for general Burmese language understanding.
- **Fine-tuning:** Telecom-specific dataset fine-tuned with Vertex AI Tuning.
- **Cloud Storage:** JSONL datasets stored in Google Cloud Storage (us-central1 region).
- **API Integration:** Chatbot queries Vertex AI endpoints to generate responses.
- **Deployment:** No continuously running endpoint; uses serverless invocation to optimize cost.

---

## Dataset Preparation

- Datasets are prepared in JSONL format.
- Telecom-specific questions and answers included.
- Stored securely in Google Cloud Storage.

---

## Contributing

Contributions are welcome! Please fork the repo and create a pull request with your improvements.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or support, please contact:

- Win Win Htet  
- Email: winhtet1997@gmail.com  
- GitHub: winhtet1997(https://github.com/winhtet1997)

---

## Acknowledgements

- Google Vertex AI Team  
- Ooredoo Myanmar for telecom data access  

---

*Thank you for using the Burmese AI Chatbot!*
