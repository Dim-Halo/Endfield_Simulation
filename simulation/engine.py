class SimEngine:
    def __init__(self):
        self.tick = 0        # 1 tick = 0.1s
        self.entities = []

    def log(self, message):
        seconds = self.tick / 10.0
        timestamp = f"[{int(seconds // 60):02}:{seconds % 60:04.1f}]"
        print(f"{timestamp} {message}")

    def run(self, max_seconds=30):
        max_ticks = int(max_seconds * 10)
        self.log(f"=== 模拟开始 (时长: {max_seconds}s) ===")
        
        for _ in range(max_ticks):
            self.tick += 1
            for entity in self.entities:
                entity.on_tick(self)
                
        self.log("=== 模拟结束 ===")