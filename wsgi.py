"""Application entry point."""
from application import create_app
import os

port = int( os.getenv( 'PORT', 8000 ) )

def main():
	app = create_app()
	app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == "__main__":
	main()