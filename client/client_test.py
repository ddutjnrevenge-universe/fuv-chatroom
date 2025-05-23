import asyncio
import socketio
import sys

sio = socketio.AsyncClient()

@sio.event
async def connect():
    print('connection established')

@sio.event
async def incoming_message(data):
    print('message received: ', data['message'])
    # await sio.emit('my response', {'response': 'my response'})

@sio.event
async def disconnect():
    print('disconnected from server')

async def send_messages():
    # Async input loop to send messages from terminal
    print("Type your messages below. Type 'quit' to exit.")
    loop = asyncio.get_running_loop()
    while True:
        # Run the blocking input() call in a separate thread to not block event loop
        message = await loop.run_in_executor(None, sys.stdin.readline)
        message = message.strip()
        if message.lower() == 'quit':
            print("Quitting...")
            await sio.disconnect()
            break
        if message:
            await sio.emit('chat_message', {'message': message})

async def main():
    try:
        await sio.connect('http://localhost:8080', wait_timeout=10)
        print("Connected successfully")

        # Start the send_messages coroutine concurrently with sio.wait()
        await asyncio.gather(
            send_messages(),
            sio.wait()
        )
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
