from flask import Flask, abort, request
import xmltodict
from pprint import pprint
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import paramiko
import time

server = Flask(__name__)

global widget_data
widget_data = {}

global roomkit_access_data
roomkit_access_data = {
    "ip_address": "10.10.143.100",
    "login": "admin",
    "password": "Qwerty123"
}

global phone_access_data
phone_access_data = {
    "ip_address": "10.10.137.101",
    "login": "screenshotuser",
    "password": "Qwerty123"
}

global wifi_access_data
wifi_access_data = {
    "ip_address": "10.10.136.7",
    "login": "uc",
    "password": "Qwerty123"
}

global ap_list
ap_list = ["AP3802I-UC","AP3802I-APC","AP3802E"]

@server.route('/', methods=['GET', 'POST'])
def codec():

    print("Получен HTTP запрос " + request.method)

    if not request.json:
        print("Нет JSON внутри HTTP запроса")
        return "OK"

    json_data = request.json

    event = []

    try:
        event = (json_data['Event']['UserInterface']['Extensions']['Panel']['Clicked']['PanelId']['Value']).split(":")
        print('Приехало событие от панельки')
    except KeyError:
        print('Сработало исключение для панельки')

    #try:
    #    event = (json_data['Event']['UserInterface']['Extensions']['Event']['Pressed']['Signal']['Value']).split(":")
    #    print('Приехало событие от виджета - Pressed')
    #except KeyError:
    #    print('Сработало исключение для виджета - Pressed')

    try:
        event = (json_data['Event']['UserInterface']['Extensions']['Event']['Clicked']['Signal']['Value']).split(":")
        print('Приехало событие от виджета Clicked')
    except KeyError:
        print('Сработало исключение для виджета Clicked')

    if event:
        if event[0] == "CoffeService":
            # Обработка для открытия панельки
            print ("Обрабатываем событие открытия панельки Кофе")
            get_value(roomkit_access_data)
            if "CoffeeCount" in widget_data:
                if widget_data["CoffeeCount"] is None:
                     set_value(roomkit_access_data, "CoffeeCount", "0")
            if "TeaCount" in widget_data:
                if widget_data["TeaCount"] is None:
                     set_value(roomkit_access_data, "TeaCount", "0")

        elif event[0] == "CoffeeCount":
            # Обработка для изменения количества кофе
            if event[1] == "increment":
                widget_data[event[0]] = str(int(widget_data[event[0]]) + 1)
                set_value(roomkit_access_data, event[0], widget_data[event[0]])
                print("Обрабатываем событие увелечения кофе")
            elif (event[1] == "decrement") and (int(widget_data[event[0]]) >= 1):
                widget_data[event[0]] = str(int(widget_data[event[0]]) - 1)
                set_value(roomkit_access_data, event[0], widget_data[event[0]])
                print("Обрабатываем событие уменьшения кофе")

        elif event[0] == "TeaCount":
            # Обработка для изменения количества  чая
            print(event[0])
            if event[1] == "increment":
                widget_data[event[0]] = str(int(widget_data[event[0]]) + 1)
                set_value(roomkit_access_data, event[0], widget_data[event[0]])
                print("Обрабатываем событие увелечения чая")
            elif (event[1] == "decrement") and (int(widget_data[event[0]]) >= 1):
                widget_data[event[0]] = str(int(widget_data[event[0]]) - 1)
                set_value(roomkit_access_data, event[0], widget_data[event[0]])
                print("Обрабатываем событие уменьшения чая")

        elif event[0] == "SendButton":
            # Обработка отправки заказа
            print("Обрабатываем событие отправки заказа")
            send_order()

        elif event[0] == "WiFiService":
            # Обработка для открытия панельки
            print ("Обрабатываем событие открытия панельки WiFi")

        elif event[0] == "APLedOn":
            print("Обрабатываем ссбытие включения новогоднего режима")
            set_wifi_led_mode("indefinite", ap_list)

        elif event[0] == "APLedOff":
            print("Обрабатываем ссбытие выключения новогоднего режима")
            set_wifi_led_mode("disable", ap_list)

        else:
            #что-то непонятное, неизвестный виджет - ничего не делаем
            print("Какое-то непонятное событие - ничего не делаем")

    else:
        print("В HTTP запросе пусто - выросла капуста")

    return 'OK'

@server.route('/SubmitOrder', methods=['GET', 'POST'])
def submit_order():

    print("Получен HTTP запрос - подтверждение заказа: " + request.method)
    set_value(roomkit_access_data, "CoffeeCount", "0")
    set_value(roomkit_access_data, "TeaCount", "0")
    widget_data["CoffeeCount"] = "0"
    widget_data["TeaCount"] = "0"

    # URL
    http_url = "http://" + roomkit_access_data["ip_address"] + "/putxml"

    # HTTP Headers
    http_headers = {'Content-Type': 'text/xml'}

    http_data = """
<Command>
	<UserInterface>
		<Message>
			<Alert>
				<Display>
					<Duration>15</Duration>
                    <Text>Заказ принят</Text>
                </Display>
            </Alert>
        </Message>
    </UserInterface>
</Command>"""

    # disable warning about untrusted certs
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Create the Requests Connection
    try:
        post = requests.post(http_url, data=http_data.encode('utf-8'), headers=http_headers, verify=False, auth=(roomkit_access_data["login"], roomkit_access_data["password"]))
    except requests.exceptions.ConnectionError:
        console_output = "Ошибка соединения с сервером " + roomkit_access_data["ip_address"]
        print(console_output)
        return "OK"
    except:
        console_output = "Что-то пошло не так при подключении пользователя " + roomkit_access_data["login"] + " к серверу " + roomkit_access_data["ip_address"]
        print(console_output)
        return "OK"

    # Check is answer is successful
    if post.status_code == 401:
        console_output = "Пользователь " + roomkit_access_data["login"] + " не авторизован для подключения к серверу " + roomkit_access_data["ip_address"]
        print(console_output)
        return "OK"

    if post.status_code != 200:
        console_output = "Ошибка при подключении к серверу: " + str(post.status_code) + ": " + post.reason
        print(console_output)
        return "OK"

    # Convert output to Dict
    console_output = "Данные получены от " + roomkit_access_data["ip_address"]
    print(console_output)

    return '<CiscoIPPhoneText><Title>Заказ</Title><Text>Заказ подтвержден</Text><SoftKeyItem><Name>Выход</Name><URL>SoftKey:Exit</URL><Position>1</Position></SoftKeyItem></CiscoIPPhoneText>'.encode('utf-8')
    #return 'Заказ подтвержден'


def set_value(roomkit_access_data, widget_name, widget_value):

    print ("Выполняется функция установки значений виджетов set_value")
    # URL
    http_url = "http://" + roomkit_access_data["ip_address"] + "/putxml"

    # HTTP Headers
    http_headers = {'Content-Type': 'text/xml'}

    http_data = """
<Command>
  <UserInterface>
    <Extensions>
	  <Widget>
	    <SetValue> 
		  <WidgetId>""" + widget_name + """</WidgetId>
		  <Value>""" + widget_value + """</Value> 
		</SetValue>
	  </Widget>
	</Extensions>
  </UserInterface>
</Command>
    """

    # disable warning about untrusted certs
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Create the Requests Connection
    try:
        post = requests.post(http_url, data=http_data, headers=http_headers, verify=False, auth=(roomkit_access_data["login"], roomkit_access_data["password"]))
    except requests.exceptions.ConnectionError:
        console_output = "Ошибка соединения с сервером " + roomkit_access_data["ip_address"]
        print(console_output)
        return
    except:
        console_output = "Что-то пошло не так при подключении пользователя " + roomkit_access_data["login"] + " к серверу " + roomkit_access_data["ip_address"]
        print(console_output)
        return

    # Check is answer is successful
    if post.status_code == 401:
        console_output = "Пользователь " + roomkit_access_data["login"] + " не авторизован для подключения к серверу " + roomkit_access_data["ip_address"]
        print(console_output)
        return


    if post.status_code != 200:
        console_output = "Ошибка при подключении к серверу: " + str(post.status_code) + ": " + post.reason
        print(console_output)
        return

    # Convert output to Dict
    console_output = "Данные получены от " + roomkit_access_data["ip_address"]
    print(console_output)


def get_value(roomkit_access_data):

    print("Выполняется функция считывания значений виджетов get_value")

    # URL
    http_url = "http://" + roomkit_access_data["ip_address"] + "/getxml"

    # HTTP Headers
    http_headers = {'Content-Type': 'text/xml'}

    http_params = {"location": "/Status/UserInterface/Extensions"}

    # disable warning about untrusted certs
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Create the Requests Connection
    try:
        get = requests.get(http_url, params=http_params, headers=http_headers, verify=False, auth=(roomkit_access_data["login"], roomkit_access_data["password"]))
    except requests.exceptions.ConnectionError:
        console_output = "Ошибка соединения с сервером " + roomkit_access_data["ip_address"]
        print(console_output)
        return
    except:
        console_output = "Что-то пошло не так при подключении пользователя " + roomkit_access_data["login"] + " к серверу " + roomkit_access_data["ip_address"]
        print(console_output)
        return

    # Check is answer is successful
    if get.status_code == 401:
        console_output = "Пользователь " + roomkit_access_data["login"] + " не авторизован для подключения к серверу " + roomkit_access_data["ip_address"]
        print(console_output)
        return

    if get.status_code != 200:
        console_output = "Ошибка при подключении к серверу: " + str(get.status_code) + ": " + get.reason
        print(console_output)
        return

    # Convert output to Dict
    console_output = "Данные получены от " + roomkit_access_data["ip_address"]
    print(console_output)

    xml_dict = xmltodict.parse(get.text)

    # Get Dict with phones
    widget_list = xml_dict["Status"]["UserInterface"]["Extensions"]["Widget"]

    if type(widget_list) is list:
        for widget in widget_list:
            widget_data[widget["WidgetId"]] = widget["Value"]

    print("Установлены исходные значения для виджетов:")
    pprint(widget_data)

def send_order():

    print("Отправляем заказ")


    # URL
    http_url = "http://" + phone_access_data["ip_address"] + "/CGI/Execute"

    # HTTP Headers
    http_headers = {'Content-Type': 'text/xml; charset=utf-8'}

    message = "Прошу подать следующие напитки \nКофе: " + widget_data["CoffeeCount"] + "\n" + "Чай: " + widget_data["TeaCount"]
    http_data = 'XML=<?xml version="1.0" encoding="utf-8" ?><CiscoIPPhoneText><Title>Конференц-зал</Title><Text>' + message  + '</Text><SoftKeyItem><Name>Подтвердить</Name><URL method="post">http://10.10.143.108:5000/SubmitOrder</URL><Position>4</Position></SoftKeyItem></CiscoIPPhoneText>'

    # disable warning about untrusted certs
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Create the Requests Connection
    try:
        post = requests.post(http_url, data=http_data.encode('utf-8'), headers=http_headers, verify=False, auth=(phone_access_data["login"], phone_access_data["password"]))
    except requests.exceptions.ConnectionError:
        console_output = "Ошибка соединения с сервером " + phone_access_data["ip_address"]
        print(console_output)
        return
    except:
        console_output = "Что-то пошло не так при подключении пользователя " + phone_access_data["login"] + " к серверу " + phone_access_data["ip_address"]
        print(console_output)
        return

    # Check is answer is successful
    if post.status_code == 401:
        console_output = "Пользователь " + phone_access_data["login"] + " не авторизован для подключения к серверу " + phone_access_data["ip_address"]
        print(console_output)
        return

    if post.status_code != 200:
        console_output = "Ошибка при подключении к серверу: " + str(post.status_code) + ": " + post.reason
        print(console_output)
        return

    # Convert output to Dict
    console_output = "Данные получены от " + phone_access_data["ip_address"]
    print(console_output)

    http_data = 'XML= <CiscoIPPhoneExecute><ExecuteItem URL="Play:Chime.raw" /></CiscoIPPhoneExecute>'

    # Create the Requests Connection
    try:
        post = requests.post(http_url, data=http_data, headers=http_headers, verify=False, auth=(phone_access_data["login"], phone_access_data["password"]))
    except requests.exceptions.ConnectionError:
        console_output = "Ошибка соединения с сервером " + phone_access_data["ip_address"]
        print(console_output)
        returm
    except:
        console_output = "Что-то пошло не так при подключении пользователя " + phone_access_data["login"] + " к серверу " + phone_access_data["ip_address"]
        print(console_output)
        return

    # Check is answer is successful
    if post.status_code == 401:
        console_output = "Пользователь " + phone_access_data["login"] + " не авторизован для подключения к серверу " + phone_access_data["ip_address"]
        print(console_output)
        return

    if post.status_code != 200:
        console_output = "Ошибка при подключении к серверу: " + str(post.status_code) + ": " + post.reason
        print(console_output)
        return

    # Convert output to Dict
    console_output = "Данные получены от " + phone_access_data["ip_address"]
    print(console_output)

def set_wifi_led_mode(led_mode, ap_list):

    print("Изменение новогоднего режима AP")

    shell_command = "config ap led-state flash " + led_mode + " "

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  #
    try:
        client.connect(wifi_access_data["ip_address"], username=wifi_access_data["login"], password=wifi_access_data["password"])
        channel = client.invoke_shell()
        channel.send(wifi_access_data["login"])
        channel.send("\n")
        time.sleep(0.5)
        channel.send(wifi_access_data["password"])
        channel.send("\n")

        for ap in ap_list:
            channel.send(shell_command + ap)
            channel.send("\r\n")
            time.sleep(0.5)


        output = channel.recv(128)

    except:
        client.close()
        print("Не получилось отправить команду на консоль беспроводного контроллера!")
        return

    client.close()
    console_output = output
    print(console_output)

if __name__ == '__main__':
    server.run(host='0.0.0.0', port=5000, debug=True)