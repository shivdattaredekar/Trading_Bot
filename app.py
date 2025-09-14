import argparse
from auth_manager import AuthManager

def main():
    parser = argparse.ArgumentParser(description="FYERS Authentication Manager")
    parser.add_argument("--login", action="store_true", help="Trigger login or refresh tokens")

    args = parser.parse_args()

    if args.login:
        auth = AuthManager()
        auth.auto_login()

if __name__ == "__main__":
    main()
