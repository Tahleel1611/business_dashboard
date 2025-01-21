# Business Dashboard

This project is a business dashboard application built with Python. It provides various analytics and visualizations to help businesses make informed decisions.

## Features

- Data visualization
- Real-time analytics
- Customizable dashboards
- User authentication and authorization

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/business_dashboard.git
   ```
2. Navigate to the project directory:
   ```bash
   cd business_dashboard
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Database

for connecting to database either change the database settings in settings.py ,to your required
database or to use without any changes use mysql as database and create database called 'dashboard_db'.

## Usage

0. use virtual env shell:
   ```bash
   pipenv shell
   ```
1. For database:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
2. Run the application:
   ```bash
   python manage.py runserver
   ```
3. Open your web browser and go to `http://localhost:8000`.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any inquiries, please contact [tahleel.banday16@gmail.com].
