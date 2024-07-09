import json
import os
from datetime import datetime
import hashlib
import secrets
import re
import logging

# Configuración de logging
logging.basicConfig(filename='atm.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

ACCOUNTS_FILE = "accounts.json"
MAX_LOGIN_ATTEMPTS = 3
SALT_LENGTH = 16

def hash_password(password, salt=None):
    if not salt:
        salt = secrets.token_hex(SALT_LENGTH)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                  salt.encode('ascii'), 100000)
    return pwdhash.hex() + ':' + salt

def check_password(stored_password, provided_password):
    pwdhash, salt = stored_password.split(':')
    return pwdhash == hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), 
                                          salt.encode('ascii'), 100000).hex()

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as file:
            return json.load(file)
    return {}

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w") as file:
        json.dump(accounts, file, indent=2)

def generate_account_number(accounts):
    while True:
        new_account = secrets.randbelow(9000) + 1000  # Genera número entre 1000 y 9999
        if str(new_account) not in accounts:
            return str(new_account)

def validate_pin(pin):
    return re.match(r'^\d{4}$', pin) is not None

def create_account(accounts):
    print("\nCreación de nueva cuenta (Escriba 'cancelar' en cualquier momento para abortar)")
    
    account_number = generate_account_number(accounts)
    print(f"Número de cuenta generado: {account_number}")
    
    while True:
        pin = input("Ingrese el PIN (4 dígitos): ")
        if pin.lower() == 'cancelar':
            print("Creación de cuenta cancelada.")
            return
        if validate_pin(pin):
            break
        print("El PIN debe ser de 4 dígitos numéricos. Intente nuevamente.")
    
    while True:
        account_type = input("Tipo de cuenta (1: Ahorro, 2: Corriente): ")
        if account_type.lower() == 'cancelar':
            print("Creación de cuenta cancelada.")
            return
        if account_type in ['1', '2']:
            break
        print("Tipo de cuenta inválido. Intente nuevamente.")
    
    while True:
        initial_balance_input = input("Ingrese el saldo inicial: ")
        if initial_balance_input.lower() == 'cancelar':
            print("Creación de cuenta cancelada.")
            return
        try:
            initial_balance = float(initial_balance_input)
            if initial_balance >= 0:
                break
            print("El saldo inicial no puede ser negativo. Intente nuevamente.")
        except ValueError:
            print("Saldo inválido. Intente nuevamente.")
    
    # Confirmar detalles
    print("\nConfirme los detalles de la cuenta:")
    print(f"Número de cuenta: {account_number}")
    print(f"Tipo de cuenta: {'Ahorro' if account_type == '1' else 'Corriente'}")
    print(f"Saldo inicial: ${initial_balance:.2f}")
    
    confirm = input("¿Son correctos estos detalles? (s/n): ")
    if confirm.lower() != 's':
        print("Creación de cuenta cancelada.")
        return
    
    # Crear la cuenta
    hashed_pin = hash_password(pin)
    accounts[account_number] = {
        "pin": hashed_pin,
        "balance": initial_balance,
        "type": "Ahorro" if account_type == "1" else "Corriente",
        "transactions": [],
        "login_attempts": 0
    }
    save_accounts(accounts)
    logging.info(f"Nueva cuenta creada: {account_number}")
    print(f"Cuenta {account_number} creada exitosamente.")

def login(accounts):
    account_number = input("Ingrese su número de cuenta: ")
    if account_number not in accounts:
        logging.warning(f"Intento de acceso a cuenta inexistente: {account_number}")
        print("Cuenta no encontrada.")
        return None
    
    account = accounts[account_number]
    if account["login_attempts"] >= MAX_LOGIN_ATTEMPTS:
        logging.warning(f"Cuenta bloqueada: {account_number}")
        print("Cuenta bloqueada. Por favor, contacte al servicio al cliente.")
        return None
    
    pin = input("Ingrese su PIN: ")
    if check_password(account["pin"], pin):
        account["login_attempts"] = 0
        save_accounts(accounts)
        logging.info(f"Inicio de sesión exitoso: {account_number}")
        return account_number
    else:
        account["login_attempts"] += 1
        save_accounts(accounts)
        logging.warning(f"Intento de login fallido: {account_number}")
        print("PIN incorrecto.")
        if account["login_attempts"] >= MAX_LOGIN_ATTEMPTS:
            logging.warning(f"Cuenta bloqueada por múltiples intentos fallidos: {account_number}")
            print("Cuenta bloqueada debido a múltiples intentos fallidos.")
        return None

def check_balance(accounts, account_number):
    print(f"Su saldo actual es: ${accounts[account_number]['balance']:.2f}")

def withdraw(accounts, account_number):
    amount = float(input("Ingrese la cantidad a retirar: "))
    if amount <= 0:
        print("La cantidad debe ser positiva.")
        return
    if amount > accounts[account_number]["balance"]:
        print("Saldo insuficiente.")
    else:
        accounts[account_number]["balance"] -= amount
        accounts[account_number]["transactions"].append({
            "type": "retiro",
            "amount": -amount,
            "date": datetime.now().isoformat()
        })
        save_accounts(accounts)
        logging.info(f"Retiro exitoso: {account_number}, cantidad: {amount}")
        print(f"Retiro exitoso. Su nuevo saldo es: ${accounts[account_number]['balance']:.2f}")

def deposit(accounts, account_number):
    amount = float(input("Ingrese la cantidad a depositar: "))
    if amount <= 0:
        print("La cantidad debe ser positiva.")
        return
    accounts[account_number]["balance"] += amount
    accounts[account_number]["transactions"].append({
        "type": "depósito",
        "amount": amount,
        "date": datetime.now().isoformat()
    })
    save_accounts(accounts)
    logging.info(f"Depósito exitoso: {account_number}, cantidad: {amount}")
    print(f"Depósito exitoso. Su nuevo saldo es: ${accounts[account_number]['balance']:.2f}")

def transfer(accounts, account_number):
    recipient = input("Ingrese el número de cuenta del destinatario: ")
    if recipient not in accounts:
        print("Cuenta de destinatario no encontrada.")
        return
    
    amount = float(input("Ingrese la cantidad a transferir: "))
    if amount <= 0:
        print("La cantidad debe ser positiva.")
        return
    if amount > accounts[account_number]["balance"]:
        print("Saldo insuficiente.")
    else:
        accounts[account_number]["balance"] -= amount
        accounts[recipient]["balance"] += amount
        transaction_date = datetime.now().isoformat()
        accounts[account_number]["transactions"].append({
            "type": "transferencia enviada",
            "amount": -amount,
            "date": transaction_date
        })
        accounts[recipient]["transactions"].append({
            "type": "transferencia recibida",
            "amount": amount,
            "date": transaction_date
        })
        save_accounts(accounts)
        logging.info(f"Transferencia exitosa: de {account_number} a {recipient}, cantidad: {amount}")
        print(f"Transferencia exitosa. Su nuevo saldo es: ${accounts[account_number]['balance']:.2f}")

def change_pin(accounts, account_number):
    current_pin = input("Ingrese su PIN actual: ")
    if not check_password(accounts[account_number]["pin"], current_pin):
        logging.warning(f"Intento fallido de cambio de PIN: {account_number}")
        print("PIN incorrecto.")
        return
    
    new_pin = input("Ingrese su nuevo PIN (4 dígitos): ")
    if not validate_pin(new_pin):
        print("El PIN debe ser de 4 dígitos numéricos.")
        return
    
    accounts[account_number]["pin"] = hash_password(new_pin)
    save_accounts(accounts)
    logging.info(f"PIN cambiado exitosamente: {account_number}")
    print("PIN cambiado exitosamente.")

def print_mini_statement(accounts, account_number):
    print("\n--- Mini Estado de Cuenta ---")
    for transaction in accounts[account_number]["transactions"][-5:]:
        print(f"{transaction['date']} - {transaction['type'].capitalize()}: ${abs(transaction['amount']):.2f}")
    print(f"Saldo actual: ${accounts[account_number]['balance']:.2f}")

def generate_summary_report(accounts):
    print("\n--- Reporte Resumen de Cuentas ---")
    print(f"Total de cuentas: {len(accounts)}")
    total_balance = sum(account['balance'] for account in accounts.values())
    print(f"Balance total de todas las cuentas: ${total_balance:.2f}")
    print("\nResumen por cuenta:")
    for account_number, account in accounts.items():
        print(f"Cuenta: {account_number}, Tipo: {account['type']}, Saldo: ${account['balance']:.2f}")

def generate_detailed_report(accounts, account_number):
    if account_number not in accounts:
        print("Cuenta no encontrada.")
        return
    
    account = accounts[account_number]
    print(f"\n--- Reporte Detallado de la Cuenta {account_number} ---")
    print(f"Tipo de cuenta: {account['type']}")
    print(f"Saldo actual: ${account['balance']:.2f}")
    print(f"Número de intentos de inicio de sesión fallidos: {account['login_attempts']}")
    print("\nHistorial de transacciones:")
    for transaction in account['transactions']:
        print(f"{transaction['date']} - {transaction['type'].capitalize()}: ${abs(transaction['amount']):.2f}")

def admin_menu(accounts):
    while True:
        print("\n--- Menú de Administrador ---")
        print("1. Generar reporte resumen de todas las cuentas")
        print("2. Generar reporte detallado de una cuenta específica")
        print("3. Volver al menú principal")
        
        choice = input("Seleccione una opción: ")
        
        if choice == "1":
            generate_summary_report(accounts)
        elif choice == "2":
            account_number = input("Ingrese el número de cuenta para el reporte detallado: ")
            generate_detailed_report(accounts, account_number)
        elif choice == "3":
            break
        else:
            print("Opción inválida. Intente de nuevo.")

def main():
    accounts = load_accounts()
    
    while True:
        print("\n--- Bienvenido al Cajero Automático Seguro ---")
        print("1. Crear cuenta")
        print("2. Iniciar sesión")
        print("3. Acceso de administrador")
        print("4. Salir")
        
        choice = input("Seleccione una opción: ")
        
        if choice == "1":
            create_account(accounts)
        elif choice == "2":
            account_number = login(accounts)
            if account_number:
                while True:
                    print(f"\nCuenta: {account_number} - Tipo: {accounts[account_number]['type']}")
                    print("1. Consultar saldo")
                    print("2. Retirar dinero")
                    print("3. Depositar dinero")
                    print("4. Transferir dinero")
                    print("5. Cambiar PIN")
                    print("6. Mini estado de cuenta")
                    print("7. Cerrar sesión")
                    
                    option = input("Seleccione una opción: ")
                    
                    if option == "1":
                        check_balance(accounts, account_number)
                    elif option == "2":
                        withdraw(accounts, account_number)
                    elif option == "3":
                        deposit(accounts, account_number)
                    elif option == "4":
                        transfer(accounts, account_number)
                    elif option == "5":
                        change_pin(accounts, account_number)
                    elif option == "6":
                        print_mini_statement(accounts, account_number)
                    elif option == "7":
                        logging.info(f"Sesión cerrada: {account_number}")
                        print("Sesión cerrada. Gracias por usar nuestro cajero.")
                        break
                    else:
                        print("Opción inválida. Intente de nuevo.")
        elif choice == "3":
            admin_password = input("Ingrese la contraseña de administrador: ")
            if admin_password == "admin123":  # En un sistema real, usa una autenticación más segura
                admin_menu(accounts)
            else:
                logging.warning("Intento fallido de acceso al menú de administrador")
                print("Contraseña incorrecta.")
        elif choice == "4":
            print("Gracias por usar nuestro cajero automático seguro. ¡Hasta luego!")
            break
        else:
            print("Opción inválida. Intente de nuevo.")

if __name__ == "__main__":
    main()
