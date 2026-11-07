# Mobile App Structure (React Native + Expo)

## Navigation Flow
1. **(tabs) - Main Bottom Navigation**
   - **Home (หน้าแรก)**: แสดงรายการห้องและกริดอุปกรณ์ (Room-based Device Grid) สไตล์ Smart Life
   - **Smart (ฉากอัตโนมัติ)**: จัดการ Automation และ Scenes
   - **Me (โปรไฟล์)**: ตั้งค่า Workspace และข้อมูลผู้ใช้

2. **(modals & stack) - Secondary Screens**
   - **DeviceDetailScreen**: หน้าปรับแต่งค่าอุปกรณ์เชิงลึก (เช่น หรี่แสงไฟ, ปรับอุณหภูมิแอร์)
   - **AddDeviceScreen**: สแกนและเพิ่มอุปกรณ์ Smart Device ใหม่
   - **RoomManagementScreen**: จัดการเพิ่ม/ลบห้องและจัดระเบียบอุปกรณ์
