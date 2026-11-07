import { Controller, Get, Patch, Param, Body } from '@nestjs/common';

@Controller('api/v1/devices')
export class DevicesController {
  @Get()
  findAll() {
    return [
      { id: 'dev-1', name: 'ปั๊มน้ำหลัก (โซน A)', room: 'แปลงเกษตรโซน A', isOn: true },
      { id: 'dev-2', name: 'ระบบพ่นหมอกโรงเรือน', room: 'โรงเรือนเพาะชำ', isOn: false },
      { id: 'dev-3', name: 'วาล์วน้ำหยด (โซน B)', room: 'แปลงเกษตรโซน B', isOn: true },
    ];
  }

  @Patch(':id/state')
  updateState(@Param('id') id: string, @Body('isOn') isOn: boolean) {
    console.log(`[Hardware Command] Device ${id} state changed to: ${isOn}`);
    return { success: true, deviceId: id, isOn };
  }
}
