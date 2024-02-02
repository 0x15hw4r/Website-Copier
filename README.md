# Website Copier

Welcome to the Website Copier project repository! This project is designed to scrape website content and provide it as a downloadable zip file. It offers two types of functionality: scraping using the `wget` method and scraping using the `requests` method. It utilizes Flask, BeautifulSoup, requests, Selenium, and Flask-SocketIO for its functionalities.

## Features

- **Scraping Functionality**: Copy the content of a website and package it into a zip file for download.
- **Dynamic Content Handling**: Support for scraping websites with dynamic content using Selenium WebDriver.
- **Real-time Progress Tracking**: Monitor the progress of the scraping process in real-time using WebSocket communication.
- **Two Scraping Methods**: Supports scraping using both `requests` and `wget` methods.

## Usage

1. Clone the repository:

    ```bash
    git clone https://github.com/0x15hw4r/Website-Copier.git
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Run the Flask application:

    ```bash
    python app.py
    ```

4. Access the application in your web browser at http://localhost:5000.

5. Enter the URL of the website you want to scrape and choose the desired scraping method (requests or wget).

6. Monitor the progress of the scraping process in real-time.

7. Once the scraping is complete, download the zip file containing the scraped content.


## Contributing

Contributions to the Website Copier project are welcome! If you have any suggestions, bug fixes, or enhancements, feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Connect with Us

Stay updated with the latest news and announcements by following us on [LinkedIn](https://www.linkedin.com/in/ishwar-mhase) and [Twitter](https://twitter.com/IshwarMhase). Join our growing community of developers and enthusiasts!

## Contact

If you have any questions or need assistance, feel free to reach out via email: ishwarmhase883@gmail.com.

Happy scraping with Website Copier! 🌐📄
