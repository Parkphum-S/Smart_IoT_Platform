import { WebSocketGateway, WebSocketServer, SubscribeMessage, MessageBody } from '@nestjs/websockets';
import { Server } from 'socket.io';

@WebSocketGateway({ cors: { origin: '*' } })
export class IotGateway {
  @WebSocketServer()
  server: Server;

  @SubscribeMessage('control_device')
  handleControl(@MessageBody() data: { deviceId: string; isOn: boolean }) {
    console.log(`[WebSocket] Relay command to ESP32 -> Device: ${data.deviceId}, State: ${data.isOn}`);
    this.server.emit('device_status_changed', data);
  }
}
