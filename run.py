from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Dynamic Flask API with in-memory DB running. Access your resources at http://127.0.0.1:5000/<resource_name>")
    app.run(debug=True, host='0.0.0.0', port=5000)
