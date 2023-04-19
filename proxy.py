# @author M. Sai Supraj Reddy


from socket import *
from urllib.parse import urlparse
import sys
from pathlib import Path

# Set up a cache folder
cache_folder = Path('cache')
cache_folder.mkdir(exist_ok=True)

def handle_request(request, c_socket, server_socket):

    # Check for a propery formatted HTTP request
    request_lines = request.split('\r\n')
    if len(request_lines) < 2 or not request_lines[0].startswith('GET ') or not request_lines[0].endswith(' HTTP/1.1') or request_lines[0].endswith(' HTTP/1.0'):
        error_request = b'HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n'
        return error_request
    
    # Extract the requested URL from the request line
    url = request_lines[0].split()[1]

    # Parse the URL to get the hostname, path and port number
    url_parts = urlparse(url)
    hostname = url_parts.hostname
    port = url_parts.port if url_parts.port else 80
    path = url_parts.path if url_parts.path else '/index.html'



    # Check if the requested page is in the cache
    host_folder = Path(hostname)
    if path == '/':
        cache_file_path = cache_folder / host_folder / Path('index.html')
    else:
        cache_file_path = cache_folder / host_folder / Path(path.lstrip('/'))
    cache_file_path.parent.mkdir(parents=True, exist_ok=True)

    

    if cache_file_path.exists():
        print('File is in the cache....')
        with open(cache_file_path, 'rb') as cache_file:
            cached_response = cache_file.read()
            content_length = len(cached_response)
            header_response = 'Cache-Hit: 1\r\nContent-Length: {}\r\nConnection: close\r\n\r\n'.format(content_length)
            cached_response = header_response.encode() + cached_response
            return cached_response

    print('No Cache Hit. Requesting origin server for the file....\n')
        
    # Construct the new request to the remote server
    new_request = 'GET {} HTTP/1.1\r\n'.format(path)
    new_request += 'Host: {}\r\n'.format(hostname)
    new_request += 'Connection: close\r\n'
    new_request += '\r\n'

    final_request = new_request.encode('UTF-8')


    # Open a connection to the remote server and send the request
    r_socket = socket(AF_INET, SOCK_STREAM)
    r_socket.connect((hostname,port))
    r_socket.sendall(final_request)

    # Receive the response from the server
    response = b""
    while True:
        data = r_socket.recv(4096)
        if not data:
            break
        response += data

    status_line = response.split(b'\r\n')[0].decode('UTF-8')
    status_code = int(status_line.split()[1])
    if status_code == 200:
        # Cache the response and relay it to the client
        headers, content = response.split(b'\r\n\r\n',1)
        with open(cache_file_path, 'wb') as cache_file:
            cache_file.write(content)
        print("Successfully received the response from the origin server\r\n")
        return response.replace(headers, b'Cache-Hit: 0\r\n' + headers)
    elif status_code == 404:
        print("Resource not found on the server....")
        response = b'\r\nCache-Hit: 0\r\n' + response
        return response
    else:
        # Creating a 500 'Internal Error' message and send it to the client
        print("Not a 200 or 404 status code... Returned a 500 Internal error to the client....")
        error_response = b'\r\nHTTP/1.1 500 Internal Error\r\nCache-Hit: 0\r\nContent-Length: 0\r\n\r\n'
        return error_response
    

if __name__ == '__main__':
    # Parse the command to retrieve the port number
    if len(sys.argv) < 2:
        print('Usage: python3 proxy.py <port>')
        sys.exit(1)
    port = int(sys.argv[1])

    # Create a socket and listen for connections
    server_socket = socket(AF_INET,SOCK_STREAM)
    server_socket.bind(('localhost', port))
    server_socket.listen()

    print(f'Proxy server listening on port {port}...',end="\n")

    print('\r\n\r\n')


    # Wait for incoming client requests and process them one by one
    while True:
        print('*********************** Ready to serve ***********************')
        c_socket, c_address = server_socket.accept()
        print(f'Accepted connection from {c_address[0]}:{c_address[1]}',end="\n")
        request = c_socket.recv(4096).decode()
        print(f'Received a message from this client: {request}')
        response = handle_request(request, c_socket, server_socket)
        print("Sending the response to the client.....")
        c_socket.sendall(response)
        print("Done with the request..Closing the connection..." )
        c_socket.close()
