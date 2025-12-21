from core.config_manager import get_config

class PartyManager:
    """
    队伍管理器
    管理全队共享资源（如技力）
    """
    def __init__(self):
        self.config = get_config()
        self.max_sp = 300.0
        self.sp = 200.0
        self.sp_regen_rate = 8.0 # 每秒回复
        
    def update(self, dt: float):
        """每帧更新"""
        if self.sp < self.max_sp:
            self.sp = min(self.max_sp, self.sp + self.sp_regen_rate * dt)
            
    def try_consume_sp(self, amount: float) -> bool:
        """尝试消耗技力"""
        if self.sp >= amount:
            self.sp -= amount
            return True
        return False
        
    def add_sp(self, amount: float):
        """增加技力"""
        self.sp = min(self.max_sp, self.sp + amount)
        
    def get_sp(self) -> int:
        """获取当前技力（向下取整）"""
        return int(self.sp)
