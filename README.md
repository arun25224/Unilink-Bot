# Unilink Bot

## Overview

Unilink Bot is a custom-built Python application designed to modernise and automate internal administrative workflows for Thrive Social consulting club. Operating through the Telegram Bot API, it gives admin staff a highly accessible interface to upload physical documents, such as expense receipts and attendance sheets, and instantly convert them into structured digital data.

By utilising a custom Optical Character Recognition (OCR) pipeline powered by PaddleOCR, this tool intentionally bypasses expensive commercial no-code platforms and proprietary APIs. The entire backend is hosted on Hugging Face Spaces to handle heavy computational loads. This architecture guarantees strict data privacy, eliminates recurring software subscription costs, and provides a highly scalable technical foundation for the club's future artificial intelligence initiatives.

## System Architecture

The architecture is built on a modular, event-driven framework where a Python backend orchestrates the communication between the user interface and the engine. When a user uploads a document, the Telegram webhook triggers the Python script hosted on Hugging Face. The image is loaded directly into temporary memory, processed by the OCR engine, and the resulting text is filtered by custom logic before being sent back to the user.

| Component | Technology | Purpose |
| --- | --- | --- |
| **User Interface** | Telegram Bot API | Acts as the front-end client. It provides a familiar, chat-based environment where users can quickly upload images or PDF documents and receive extracted, structured data without installing new software. |
| **Application Logic** | Python | The core backend script that manages the entire lifecycle of a request. It handles message routing, image downloading, state-machine management, and coordinates the requests to the machine learning models. |
| **OCR Engine** | PaddleOCR | The deep learning model responsible for the actual text extraction. It is optimised to detect and recognise text from complex, noisy layouts, including faded receipts, skewed documents, and handwritten logs. |
| **Infrastructure** | Hugging Face Spaces | The cloud hosting environment that runs the Python container. It executes the heavy computational load required by the PaddleOCR models in a serverless capacity, scaling processing power as needed. |

## Core Features

The bot is designed to handle specific administrative bottlenecks through targeted data extraction and strict privacy controls.

* **Document Scanning & Image Processing:** The bot accepts standard image formats directly via the Telegram chat. Upon upload, the backend automatically handles basic image normalisation, such as compression and orientation correction, to ensure the OCR engine receives the clearest possible input.
* **Intelligent Claim Parsing:** When processing expense receipts, the OCR engine does more than extract raw text. The Python backend applies specific parsing logic to identify and isolate critical financial data. It extracts the transaction dates, total payable amounts, and vendor names, outputting them in a standardised format that can be easily copied into the club's financial accounts.
* **Attendance Digitisation:** The pipeline is designed to read both printed and handwritten attendance rosters. When processing these documents, the logic focuses on isolating names and matrix structures, converting physical sign-in sheets into clean digital text lists to track Consultant Academy participation.
* **Stateless Processing & Data Privacy:** Data protection is a core architectural principle. The bot operates entirely in memory. Uploaded images and the resulting extracted text are never written to permanent disk storage. Once the parsed data is returned to the user in the Telegram chat, the temporary memory buffer is instantly flushed, ensuring strict compliance with internal privacy standards.

## Command Directory

The application relies on a strict state-machine architecture. This ensures the bot processes images with the correct context and applies the right parsing logic based on what the user is trying to achieve.

| Command | Action |
| --- | --- |
| `/start` | Initialises the application for the user. It verifies the user's authorisation, registers their session state, and displays the main operational menu with instructions on how to use the scanning tools. |
| `/claims` | Switches the user's active session state to financial processing. The bot sends a prompt requesting a clear image of a receipt. Any image uploaded while in this state will be processed using the logic designed to extract vendor, date, and pricing information. |
| `/attendance` | Switches the user's active session state to roster processing. The bot prompts the user to upload a training attendance sheet. Images processed in this state use logic optimised for detecting lists of names and ignoring irrelevant background text. |
| `/cancel` | Acts as a hard reset for the user's current session. It aborts any active image processing, clears pending documents from the in-memory queue, and resets the bot's state to neutral, preventing the accidental processing of the wrong document type. |
