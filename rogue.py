# rogue.py
import random, os, sys, textwrap, json

# 获取当前脚本文件的绝对路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的 exe 运行
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # 如果是 Python 脚本运行
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 存档文件路径
SAVE_FILE = os.path.join(SCRIPT_DIR, 'save.json')

# 创建游戏目录（如果不存在）
os.makedirs(SCRIPT_DIR, exist_ok=True)

# 导入rich相关模块
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import ProgressBar
from rich.text import Text
from rich.layout import Layout

# 初始化rich
console = Console()

# 颜色主题
COLORS = {
    'damage': '[red]{}[/red]',
    'heal': '[green]{}[/green]',
    'event': '[yellow]{}[/yellow]',
    'normal': '[white]{}[/white]',
    'rare': '[blue]{}[/blue]',
    'epic': '[purple]{}[/purple]',
    'boss': '[red bold]{}[/red bold]',
    'elite': '[yellow bold]{}[/yellow bold]',
    'soul': '[cyan]{}[/cyan]',
    'item': '[green]{}[/green]',
}

# ---------- 存档 ----------
def load_save():
    default_save = {
        'fragments': 0,
        'shop': {'atk+5': 0, 'hp+20': 0, 'potion+1': 0},
        'forge_level': 0,  # 铁匠铺等级
        'records': {
            'highest_wave': 0,        # 最高波次
            'total_boss_kills': 0,    # 总Boss击杀
            'total_runs': 0,          # 总游戏次数
            'greed_boss_kills': 0,    # 贪婪宝箱击杀次数
        },
        'talent_tree': {
            'warrior': {
                'strength': 0,        # 力量精通
                'vitality': 0,        # 生命精通
                'shield_master': 0,   # 护盾精通
            },
            'mage': {
                'intelligence': 0,    # 智力精通
                'spellpower': 0,      # 法术强度
                'mana_shield': 0,     # 法力护盾
            }
        },
        'equipment_storage': []       # 装备仓库
    }
    
    if not os.path.exists(SAVE_FILE):
        return default_save
        
    with open(SAVE_FILE, 'r', encoding='utf-8') as f:
        save_data = json.load(f)
        # 确保新增字段存在
        for key, value in default_save.items():
            if key not in save_data:
                save_data[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in save_data[key]:
                        save_data[key][sub_key] = sub_value
        return save_data

def save_save(data):
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- 装备系统 ----------
class Equipment:
    RARITY = ['普通', '稀有', '史诗']
    TYPES = ['武器', '护甲']
    AFFIXES = {
        '力量': lambda val: {'atk': val * 3},
        '生命': lambda val: {'max_hp': val * 10},
        '吸血': lambda val: {'lifesteal': val * 0.05},  # 5%/级
        '反伤': lambda val: {'thorns': val * 2},  # 2点/级
        '暴击': lambda val: {'crit_chance': val * 0.05},  # 5%/级
    }

    def __init__(self, type_, rarity):
        self.type = type_
        self.rarity = rarity  # 0=普通, 1=稀有, 2=史诗
        self.affixes = {}
        self._generate_affixes()
    
    def _generate_affixes(self):
        # 根据稀有度决定词条数量
        affix_count = self.rarity + 1
        available_affixes = list(self.AFFIXES.keys())
        chosen = random.sample(available_affixes, affix_count)
        
        for affix in chosen:
            # 稀有度越高，词条数值越大
            value = random.randint(1, 3) * (self.rarity + 1)
            self.affixes[affix] = value

    def reforge(self):
        """重铸装备，重新随机所有词条"""
        self._generate_affixes()
    
    def get_stats(self):
        """计算装备提供的所有属性加成"""
        stats = {'atk': 0, 'max_hp': 0, 'lifesteal': 0, 'thorns': 0, 'crit_chance': 0}
        for affix, value in self.affixes.items():
            modifier = self.AFFIXES[affix](value)
            for stat, bonus in modifier.items():
                stats[stat] += bonus
        return stats
    
    def __str__(self):
        rarity_colors = ['white', 'blue', 'purple']
        rarity_symbols = ['⚪', '🔵', '🟣']
        text = Text()
        text.append(f"{rarity_symbols[self.rarity]}{self.RARITY[self.rarity]}{self.type}\n",
                   style=rarity_colors[self.rarity])
        for affix, value in self.affixes.items():
            text.append(f"  {affix} ", style='cyan')
            text.append(f"+{value}\n", style='green')
        return str(text)
    
    def to_dict(self):
        """将装备转换为可序列化的字典"""
        return {
            'type': self.type,
            'rarity': self.rarity,
            'affixes': self.affixes
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建装备实例"""
        equipment = cls(data['type'], data['rarity'])
        equipment.affixes = data['affixes']
        return equipment

# ---------- 角色 ----------
class Character:
    def __init__(self, name):
        self.name = name
        self.hp = 100
        self.max_hp = 100
        self.atk = 10
        self.souls = 0
        self.talents = []
        self.attrs = {'力量': 0, '敏捷': 0, '智力': 0}
        self.items = {'血瓶': 0}
        self.equipment = {'武器': None, '护甲': None}
        self.lifesteal = 0
        self.thorns = 0
        self.crit_chance = 0
        # 事件状态追踪
        self.event_flags = {
            'demon_pact': False,     # 是否签订恶魔契约
            'altar_sacrifice': 0,    # 祭坛献祭次数
            'holy_blessing': False,  # 是否受到天使祝福
            'curse_level': 0,        # 诅咒等级
        }
        # 结局追踪
        self.boss_kills = 0         # 击杀Boss数量
        self.defeated_greed = False # 是否击败贪婪宝箱
        
        # 持久化存档数据
        self.save_data = None      # 存档数据引用
        self.stored_equipment = [] # 装备仓库引用

    def power(self):
        base = self.atk + self.attrs['力量'] * 2
        for eq in self.equipment.values():
            if eq:
                stats = eq.get_stats()
                base += stats['atk']
        
        # 计算诅咒加成
        if self.event_flags['curse_level'] > 0:
            curse_bonus = base * (self.event_flags['curse_level'] * 0.1)
            base += curse_bonus
        
        return int(base)

    def collect(self, n):
        self.souls += n
        print(f'💀 获得 {n} 灵魂，当前 {self.souls}')
        while self.souls >= 20:
            self.souls -= 20
            self.random_upgrade()

    def random_upgrade(self):
        if random.randrange(2):
            t = random.choice(['暴击', '吸血', '护盾'])
            self.talents.append(t)
            print(f'✨ 获得天赋：{t}')
        else:
            k = random.choice(list(self.attrs))
            self.attrs[k] += 1
            print(f'📈 属性提升：{k}+1')

    def status(self):
        # 创建状态面板
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")
        
        # 生命值进度条
        hp_percentage = self.hp / self.max_hp * 100
        hp_color = "green" if hp_percentage > 50 else "yellow" if hp_percentage > 25 else "red"
        hp_bar = ProgressBar(completed=hp_percentage, width=20, complete_style=hp_color)
        
        # 添加状态信息
        table.add_row("角色", f"[bold]{self.name}[/bold]")
        table.add_row("生命", f"{hp_bar} {self.hp}/{self.max_hp}")
        table.add_row("攻击", f"{self.power()}")
        table.add_row("天赋", " ".join(f"[cyan]{t}[/cyan]" for t in self.talents))
        table.add_row("属性", " ".join(f"{k}:{v}" for k, v in self.attrs.items()))
        table.add_row("道具", " ".join(f"{k}×{v}" for k, v in self.items.items()))
        
        # 显示装备
        if any(self.equipment.values()):
            table.add_row("装备", "")
            for slot, eq in self.equipment.items():
                if eq:
                    rarity_color = ["white", "blue", "purple"][eq.rarity]
                    table.add_row("", f"[{rarity_color}]{slot}: {eq.type}[/{rarity_color}]")
        
        console.print(Panel(table, title="角色状态"))

    def use_item(self, key):
        key = str(key)
        if key == '1' and self.items['血瓶'] > 0:
            heal = min(40, self.max_hp - self.hp)
            self.hp += heal
            self.items['血瓶'] -= 1
            print(f'🧪 使用血瓶，恢复 {heal} HP!')
            return True
        return False


class Warrior(Character):
    def __init__(self, save):
        super().__init__('战士')
        self.save_data = save
        
        # 应用商店升级
        base_hp = 100 + save['shop']['hp+20'] * 20
        base_atk = 10 + save['shop']['atk+5'] * 5
        
        # 应用天赋树加成
        talents = save['talent_tree']['warrior']
        hp_bonus = base_hp * (talents['vitality'] * 0.05)  # 每级生命精通+5%生命
        atk_bonus = base_atk * (talents['strength'] * 0.1)  # 每级力量精通+10%攻击
        shield_bonus = talents['shield_master'] * 2  # 每级护盾精通多减伤2点
        
        self.hp = self.max_hp = int(base_hp + hp_bonus)
        self.atk = int(base_atk + atk_bonus)
        self.shield_reduction = shield_bonus  # 护盾减伤值
        
        self.items['血瓶'] += save['shop']['potion+1']


class Mage(Character):
    def __init__(self, save):
        super().__init__('法师')
        self.save_data = save
        
        # 应用商店升级
        base_hp = 80 + save['shop']['hp+20'] * 20
        base_atk = 8 + save['shop']['atk+5'] * 5
        
        # 应用天赋树加成
        talents = save['talent_tree']['mage']
        hp_bonus = base_hp * (talents['mana_shield'] * 0.03)  # 每级法力护盾+3%生命
        spell_power = talents['spellpower'] * 0.15  # 每级法术强度+15%法术伤害
        intelligence = talents['intelligence'] * 0.1  # 每级智力精通+10%触发概率
        
        self.hp = self.max_hp = int(base_hp + hp_bonus)
        self.atk = base_atk
        self.spell_power = spell_power
        self.magic_chance = 0.3 + intelligence  # 基础30%触发率
        
        self.items['血瓶'] += save['shop']['potion+1']

    def magic_damage(self):
        if random.random() < self.magic_chance:
            base_dmg = 10 + self.attrs['智力'] * 3
            total_dmg = int(base_dmg * (1 + self.spell_power))
            print(f'✨ 魔法飞弹！额外 {total_dmg} 点伤害')
            return total_dmg
        return 0


class Monster:
    def __init__(self, name, hp, atk, souls, is_boss=False, is_elite=False):
        self.name = name
        self.hp = hp
        self.atk = atk
        self.souls = souls
        self.is_boss = is_boss
        self.is_elite = is_elite

    def status(self):
        prefix = '👹BOSS' if self.is_boss else '👾ELITE' if self.is_elite else '👾'
        style = 'red bold' if self.is_boss else 'yellow bold' if self.is_elite else 'white'
        hp_bar = ProgressBar(completed=self.hp, width=20, complete_style=style)
        monster_panel = Table(show_header=False, box=None)
        monster_panel.add_row(
            Text(prefix, style=style),
            Text(self.name, style=style),
            Text(f"HP: {self.hp}", style=style),
            Text(f"ATK: {self.atk}", style=style)
        )
        console.print(Panel(monster_panel, title="敌人状态", style=style))


NORMAL_NAMES = [
    ('史莱姆', 25, 7, 10), ('蝙蝠', 30, 8, 10), ('哥布林', 35, 9, 12),
    ('骷髅兵', 40, 10, 12), ('狼人', 45, 11, 15), ('石像鬼', 50, 12, 15),
    ('暗影刺客', 35, 13, 15), ('剧毒蜘蛛', 30, 14, 15)
]
BOSS_NAMES = [
    ('骷髅王', 90, 16, 45), ('炎魔', 110, 18, 50)
]
ELITE_NAMES = [
    ('精英史莱姆', 40, 12, 20), ('精英蝙蝠', 45, 13, 20), ('精英哥布林', 50, 14, 20)
]
# 隐藏Boss
GREED_BOSS = ('贪婪宝箱', 150, 25, 100)  # 更高的血量、攻击和灵魂奖励

# ---------- 地牢系统 ----------
class DungeonPath:
    def __init__(self, name, difficulty, rewards_multiplier):
        self.name = name
        self.difficulty = difficulty  # 难度倍率
        self.rewards_multiplier = rewards_multiplier  # 奖励倍率

    def apply_difficulty(self, monster):
        """根据路线难度调整怪物属性"""
        monster.hp = int(monster.hp * self.difficulty)
        monster.atk = int(monster.atk * self.difficulty)
        monster.souls = int(monster.souls * self.rewards_multiplier)

PATHS = {
    'safe': DungeonPath('安全通道', 1.0, 1.0),
    'danger': DungeonPath('危险通道', 1.5, 2.0)
}

def choose_path():
    """选择前进路线"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print('\n=== 选择通道 ===')
        print('1) 安全通道 - 普通难度，普通奖励')
        print('2) 危险通道 - 50%属性提升，双倍奖励')
        choice = input('> ').strip()
        if choice == '1':
            return PATHS['safe']
        elif choice == '2':
            return PATHS['danger']
        else:
            print('请输入 1 或 2')

# ---------- 随机事件 ----------
def get_event_pool(hero):
    """根据角色状态返回可用的事件池"""
    # 基础事件
    base_events = [
        {
            'title': '神秘泉水',
            'desc': '回满生命值，但失去所有血瓶。',
            'effect': lambda h: (
                setattr(h, 'hp', h.max_hp) or
                setattr(h, 'items', {'血瓶': 0}) or
                print('💧 生命值已回满，但失去了所有血瓶！')
            ),
            'cost': 0
        },
        {
            'title': '幸运藏宝箱',
            'desc': '随机获得1-3个血瓶或10-30灵魂。',
            'effect': lambda h: (
                exec("h.items['血瓶'] += random.randint(1, 3)") or
                print(f"🎁 获得 {h.items['血瓶']} 个血瓶！")
            ) if random.random() < 0.5 else (
                setattr(h, 'souls', h.souls + random.randint(10, 30)) or
                print(f'💀 获得 {random.randint(10, 30)} 灵魂！')
            ),
            'cost': 0
        },
        {
            'title': '诡异镜像',
            'desc': '50% 概率复制当前装备的一个词条，50% 概率损失20%当前生命。',
            'effect': lambda h: handle_mirror_event(h),
            'cost': 0
        },
        {
            'title': '流浪商人',
            'desc': '15 灵魂换 1 血瓶。',
            'effect': lambda h: exec("h.items['血瓶'] += 1") or print('🛒 购买血瓶×1'),
            'cost': 15
        }
    ]
    
    # 连锁事件系统
    chain_events = []
    
    # 神秘祭坛事件链
    if not hero.event_flags['altar_sacrifice']:
        chain_events.append({
            'title': '神秘祭坛',
            'desc': '献祭30灵魂获得力量，或献祭生命获得诅咒加成。',
            'effect': lambda h: handle_altar_event(h),
            'cost': 0
        })
    elif hero.event_flags['altar_sacrifice'] and not hero.event_flags['demon_pact']:
        chain_events.append({
            'title': '恶魔契约',
            'desc': f'已献祭{hero.event_flags["altar_sacrifice"]}次，恶魔被吸引而来...',
            'effect': lambda h: handle_demon_pact(h),
            'cost': 0
        })
    elif hero.event_flags['demon_pact'] and not hero.event_flags['holy_blessing']:
        chain_events.append({
            'title': '天使审判',
            'desc': '你的灵魂已被玷污，是否寻求救赎？',
            'effect': lambda h: handle_angel_judgment(h),
            'cost': 0
        })
    
    return chain_events + base_events

def handle_altar_event(hero):
    """处理祭坛事件"""
    print('\n1) 献祭30灵魂 - 永久+5攻击')
    print('2) 献祭20%生命 - 获得诅咒加成(每层诅咒提升10%伤害)')
    choice = input('选择(1/2)> ').strip()
    
    if choice == '1':
        if hero.souls >= 30:
            hero.souls -= 30
            hero.atk += 5
            hero.event_flags['altar_sacrifice'] += 1
            print('⚔️ 获得永久攻击加成！')
        else:
            print('灵魂不足！')
    elif choice == '2':
        life_cost = int(hero.hp * 0.2)
        hero.hp -= life_cost
        hero.event_flags['curse_level'] += 1
        hero.event_flags['altar_sacrifice'] += 1
        print(f'💀 失去{life_cost}生命值，获得诅咒加成！')
        print(f'当前诅咒等级：{hero.event_flags["curse_level"]}')

def handle_demon_pact(hero):
    """处理恶魔契约事件"""
    print('\n恶魔被你的献祭吸引而来...')
    print('1) 签订契约 - 攻击翻倍，但受到伤害增加50%')
    print('2) 拒绝契约 - 保持现状')
    choice = input('选择(1/2)> ').strip()
    
    if choice == '1':
        hero.atk *= 2
        hero.event_flags['demon_pact'] = True
        print('👿 你与恶魔达成契约！攻击翻倍，但更容易受伤...')
    else:
        print('你拒绝了恶魔的诱惑。')

def handle_angel_judgment(hero):
    """处理天使审判事件"""
    print('\n天使发现了你与恶魔的契约...')
    if hero.event_flags['curse_level'] > 0:
        print('1) 寻求救赎 - 移除所有诅咒和恶魔契约，但损失50%当前生命')
        print('2) 对抗天使 - 保持现状，但永久损失20%最大生命')
        choice = input('选择(1/2)> ').strip()
        
        if choice == '1':
            hero.hp = max(1, hero.hp // 2)
            hero.event_flags['demon_pact'] = False
            hero.event_flags['curse_level'] = 0
            hero.event_flags['holy_blessing'] = True
            hero.atk = int(hero.atk * 0.5)  # 移除恶魔契约的加成
            print('� 你获得了天使的救赎！所有诅咒被移除。')
        else:
            hero.max_hp = int(hero.max_hp * 0.8)
            hero.hp = min(hero.hp, hero.max_hp)
            print('😈 你选择了堕落之路...')
    else:
        print('天使给予你祝福！')
        hero.event_flags['holy_blessing'] = True
        hero.max_hp += 20
        hero.hp += 20
        print('😇 获得天使祝福：最大生命值+20')

def handle_mirror_event(hero):
    """处理镜像事件"""
    if not any(hero.equipment.values()):
        print('你没有装备，镜像无法生效！')
        return
    
    if random.random() < 0.5:
        # 选择一个已装备的装备
        equipped = [eq for eq in hero.equipment.values() if eq]
        if equipped:
            target = random.choice(equipped)
            if target.affixes:
                # 复制一个随机词条
                affix, value = random.choice(list(target.affixes.items()))
                if affix in target.affixes:
                    target.affixes[affix] += value
                    print(f'✨ {target.type}的{affix}词条得到了强化！')
    else:
        damage = int(hero.hp * 0.2)
        hero.hp -= damage
        print(f'💔 镜像伤害了你！损失{damage}生命值')

def random_event(hero):
    if random.randrange(100) < 40:
        events = get_event_pool(hero)
        evt = random.choice(events)
        print(f'\n🎲 随机事件：{evt["title"]}')
        print(textwrap.fill(evt['desc'], width=50))
        if evt['cost']:
            print(f'(需 {evt["cost"]} 灵魂)')
        if input('接受？(y/n) > ').strip().lower() == 'y':
            if evt['cost'] > hero.souls:
                print('灵魂不足！')
            else:
                hero.souls -= evt['cost']
                evt['effect'](hero)
        else:
            print('离开。')
        input('按 Enter 继续…')


# ---------- 主循环 ----------
def forge(save, hero):
    """铁匠铺功能"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print('=== 铁匠铺 ===')
        print(f'灵魂：{hero.souls}')
        print('\n当前装备：')
        for type_, eq in hero.equipment.items():
            print(f'\n{type_}:')
            print(eq if eq else '  (无)')
        
        print('\n1) 重铸武器 (30灵魂)')
        print('2) 重铸护甲 (30灵魂)')
        print('0) 返回')
        
        choice = input('\n> ').strip()
        if choice == '0':
            return
        elif choice in ['1', '2']:
            eq_type = '武器' if choice == '1' else '护甲'
            if hero.equipment[eq_type] is None:
                print('没有可重铸的装备！')
            elif hero.souls < 30:
                print('灵魂不足！')
            else:
                hero.souls -= 30
                hero.equipment[eq_type].reforge()
                print(f'\n重铸后的{eq_type}：')
                print(hero.equipment[eq_type])
            input('按 Enter 继续...')

def show_records(save):
    """显示游戏记录"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print('=== 历史记录 ===')
    print(f'最高波次：{save["records"]["highest_wave"]}')
    print(f'总Boss击杀：{save["records"]["total_boss_kills"]}')
    print(f'贪婪宝箱击杀：{save["records"]["greed_boss_kills"]}')
    print(f'总游戏次数：{save["records"]["total_runs"]}')
    input('\n按 Enter 返回...')

def talent_tree(save):
    """天赋树界面"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print('=== 天赋树 ===')
        print(f'当前灵魂碎片：{save["fragments"]}')
        print('\n战士天赋：')
        print(f'1) 力量精通 Lv.{save["talent_tree"]["warrior"]["strength"]} - 10碎片')
        print(f'2) 生命精通 Lv.{save["talent_tree"]["warrior"]["vitality"]} - 10碎片')
        print(f'3) 护盾精通 Lv.{save["talent_tree"]["warrior"]["shield_master"]} - 15碎片')
        print('\n法师天赋：')
        print(f'4) 智力精通 Lv.{save["talent_tree"]["mage"]["intelligence"]} - 10碎片')
        print(f'5) 法术强度 Lv.{save["talent_tree"]["mage"]["spellpower"]} - 12碎片')
        print(f'6) 法力护盾 Lv.{save["talent_tree"]["mage"]["mana_shield"]} - 15碎片')
        print('\n0) 返回')
        
        choice = input('\n> ').strip()
        if choice == '0':
            return
        
        costs = {
            '1': ('warrior', 'strength', 10),
            '2': ('warrior', 'vitality', 10),
            '3': ('warrior', 'shield_master', 15),
            '4': ('mage', 'intelligence', 10),
            '5': ('mage', 'spellpower', 12),
            '6': ('mage', 'mana_shield', 15)
        }
        
        if choice in costs:
            class_name, talent_name, cost = costs[choice]
            if save['fragments'] >= cost:
                save['fragments'] -= cost
                save['talent_tree'][class_name][talent_name] += 1
                save_save(save)
                print(f'✨ {talent_name.title()} 提升到 Lv.{save["talent_tree"][class_name][talent_name]}')
            else:
                print('灵魂碎片不足！')
            input('按 Enter 继续...')

def equipment_storage(save):
    """装备仓库界面"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print('=== 装备仓库 ===')
        if not save['equipment_storage']:
            print('仓库是空的...')
        else:
            for idx, eq_data in enumerate(save['equipment_storage'], 1):
                eq = Equipment.from_dict(eq_data)
                print(f'\n{idx}) {eq}')
        print('\n0) 返回')
        choice = input('\n> ').strip()
        if choice == '0':
            return

def show_menu(title, options, show_souls=None):
    """通用菜单显示函数"""
    menu = Table(show_header=False, box=None)
    menu.add_column("Option")
    
    if show_souls is not None:
        menu.add_row(f"[cyan]当前灵魂碎片：{show_souls}[/cyan]")
        menu.add_row("")
    
    for idx, option in enumerate(options, 1):
        menu.add_row(f"[green]{idx})[/green] {option}")
    
    console.print(Panel(menu, title=f"[bold cyan]{title}[/bold cyan]"))

def run():
    save = load_save()
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        options = [
            "开始冒险",
            "商店",
            "铁匠铺",
            "天赋树",
            "装备仓库",
            "历史记录",
            "退出"
        ]
        show_menu("主菜单", options, save["fragments"])
        choice = input('> ').strip()
        if choice == '1':
            save['records']['total_runs'] += 1
            game(save)
        elif choice == '2':
            shop(save)
        elif choice == '3':
            game_save = save.copy()
            hero = Warrior(game_save)  # 创建临时角色以访问铁匠铺
            forge(save, hero)
        elif choice == '4':
            talent_tree(save)
        elif choice == '5':
            equipment_storage(save)
        elif choice == '6':
            show_records(save)
        elif choice == '7':
            sys.exit()
        else:
            print('请输入 1-7')

def game(save):
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print('=== 职业选择 ===')
        print('1) 战士')
        print('2) 法师')
        c = input('> ').strip()
        if c == '1':
            hero = Warrior(save)
            break
        elif c == '2':
            hero = Mage(save)
            break
        else:
            print('请输入 1 或 2')

    floor = 1  # 当前层数
    wave = 0   # 当前层内的关卡数
    current_path = None  # 当前选择的路线
    
    while True:
        wave += 1
        
        # 每层开始时选择路线
        if wave == 1 or wave % 4 == 0:
            current_path = choose_path()
            hero.hp = hero.max_hp  # 进入新层时回满血
            floor = (wave - 1) // 4 + 1
            if floor > 1:
                print(f'\n🏰 欢迎来到第 {floor} 层!')
                input('按 Enter 继续...')
        
        # 判断当前关是否是Boss或精英
        is_boss = wave % 4 == 0
        is_elite = wave % 2 == 0 and not is_boss
        
        # 检查隐藏Boss触发条件
        if wave == 11 and hero.items['血瓶'] >= 5 and not hero.defeated_greed:
            # 在第三层第3关触发隐藏Boss
            print('\n💎 宝箱散发出贪婪的气息...')
            print('你的血瓶引来了隐藏Boss！')
            name, hp, atk, souls = GREED_BOSS
            monster = Monster(name, hp, atk, souls, is_boss=True)
            input('按 Enter 继续...')
        # 生成对应的怪物
        elif is_boss:
            name, hp, atk, souls = random.choice(BOSS_NAMES)
            monster = Monster(name, hp, atk, souls, is_boss=True)
        elif is_elite:
            name, hp, atk, souls = random.choice(ELITE_NAMES)
            monster = Monster(name, hp, atk, souls, is_elite=True)
        else:
            name, hp, atk, souls = random.choice(NORMAL_NAMES)
            monster = Monster(name, hp, atk, souls)
        
        # 根据选择的路线调整怪物属性
        current_path.apply_difficulty(monster)

        os.system('cls' if os.name == 'nt' else 'clear')
        print(f'\n--- 第 {floor} 层 {wave % 4 or 4}/{4} 关 [{current_path.name}] ---')
        hero.status()
        monster.status()

        while monster.hp > 0 and hero.hp > 0:
            print('\n[A]攻击  [R]逃跑  [1]血瓶' +
                  (f'({hero.items["血瓶"]})' if hero.items['血瓶'] else '(无)'))
            cmd = input('> ').strip().upper()
            if cmd == '1':
                if not hero.use_item('1'):
                    print('❌ 没有血瓶!')
                continue
            elif cmd == 'A':
                dmg = hero.power()
                if '暴击' in hero.talents and random.randrange(4) == 0:
                    dmg *= 2
                    print('⚡暴击!')
                if isinstance(hero, Mage):
                    dmg += hero.magic_damage()
                monster.hp -= dmg
                console.print(f'造成[red bold]{dmg}[/red bold]点伤害!')
                if monster.hp <= 0:
                    break
            elif cmd == 'R':
                if random.randrange(2):
                    print('成功逃跑!')
                    break
                else:
                    print('逃跑失败!')
            else:
                continue

            m_dmg = monster.atk
            if '护盾' in hero.talents:
                m_dmg = max(1, m_dmg - 5)
            
            # 恶魔契约效果：受到的伤害增加50%
            if hero.event_flags['demon_pact']:
                m_dmg = int(m_dmg * 1.5)
            
            # 计算装备提供的额外属性
            for eq in hero.equipment.values():
                if eq:
                    stats = eq.get_stats()
                    hero.max_hp += stats['max_hp']
                    hero.lifesteal = stats['lifesteal']
                    hero.thorns = stats['thorns']
                    hero.crit_chance = stats['crit_chance']
            
            # 反伤
            if hero.thorns > 0:
                thorns_dmg = hero.thorns
                monster.hp -= thorns_dmg
                print(f'⚔ 反弹{thorns_dmg}点伤害!')
            
            hero.hp -= m_dmg
            print(f'{monster.name}反击{m_dmg}点伤害!')
            
            if hero.hp <= 0:
                break

        if monster.hp <= 0:
            print(f'\n{monster.name}被击败!')
            hero.collect(monster.souls)
            
            # 装备掉落
            if monster.is_boss:
                hero.boss_kills += 1
                if monster.name == GREED_BOSS[0]:
                    hero.defeated_greed = True
                    hero.items['血瓶'] += 3
                    print('💎 击败贪婪宝箱！获得3个血瓶！')
                    # 贪婪宝箱必定掉落史诗装备
                    type_ = random.choice(Equipment.TYPES)
                    equip = Equipment(type_, 2)  # 史诗品质
                    print(f'\n获得传说装备：\n{equip}')
                    if input('是否装备？(y/n) > ').lower() == 'y':
                        hero.equipment[type_] = equip
                else:
                    hero.items['血瓶'] += 1
                    print('🧪 Boss 必掉血瓶×1!')
                    # Boss必定掉落稀有或史诗装备
                    rarity = random.randint(1, 2)
                    type_ = random.choice(Equipment.TYPES)
                    equip = Equipment(type_, rarity)
                    print(f'\n获得装备：\n{equip}')
                    if input('是否装备？(y/n) > ').lower() == 'y':
                        hero.equipment[type_] = equip
            elif monster.is_elite:
                # 精英40%掉落装备
                if random.random() < 0.4:
                    rarity = random.randint(0, 1)  # 普通或稀有
                    type_ = random.choice(Equipment.TYPES)
                    equip = Equipment(type_, rarity)
                    print(f'\n获得装备：\n{equip}')
                    if input('是否装备？(y/n) > ').lower() == 'y':
                        hero.equipment[type_] = equip
            elif random.random() < 0.2:  # 普通怪20%掉落
                type_ = random.choice(Equipment.TYPES)
                equip = Equipment(type_, 0)  # 普通品质
                print(f'\n获得装备：\n{equip}')
                if input('是否装备？(y/n) > ').lower() == 'y':
                    hero.equipment[type_] = equip
            
            # 血瓶掉落
            elif random.randrange(2) == 0:
                hero.items['血瓶'] += 1
                print('🧪 获得血瓶×1!')
            
            # 吸血效果
            if '吸血' in hero.talents or hero.lifesteal > 0:
                heal = min(10 + int(hero.lifesteal * dmg), hero.max_hp - hero.hp)
                hero.hp += heal
                print(f'吸血恢复{heal}HP')
            if monster.is_boss and wave < 12:  # 最后一层boss不需要选择
                random_event(hero)
                print('\n🚪 你在前方发现了两个通道...')
                input('按 Enter 继续...')
            else:
                input('按 Enter 继续…')

        if hero.hp <= 0:
            fragments = wave * 5 + hero.souls // 2
            save['fragments'] += fragments
            save_save(save)
            print(f'\n💀 你阵亡在第 {wave} 关！')
            print(f'获得灵魂碎片 {fragments}，累计 {save["fragments"]}')
            if input('输入 q 重新开始 > ').strip().lower() == 'q':
                return
            else:
                sys.exit()

        if wave >= 12:  # 3层×4关=12关
            # 更新记录
            save['records']['highest_wave'] = max(save['records']['highest_wave'], wave)
            save['records']['total_boss_kills'] += hero.boss_kills
            if hero.defeated_greed:
                save['records']['greed_boss_kills'] += 1
            
            # 计算通关奖励（考虑难度加成）
            base_fragments = 150
            total_multiplier = sum(PATHS[p].rewards_multiplier for p in ['safe', 'danger']) / 2
            
            # 额外奖励：击败隐藏Boss
            if hero.defeated_greed:
                base_fragments += 100
            
            fragments = int(base_fragments * total_multiplier) + hero.souls
            save['fragments'] += fragments
            
            # 存储装备到仓库
            for eq in hero.equipment.values():
                if eq and (eq.rarity >= 1 or input(f'是否保存{eq.type}到仓库？(y/n) > ').lower() == 'y'):
                    save['equipment_storage'].append(eq.to_dict())
                    print(f'已将{eq.RARITY[eq.rarity]}{eq.type}存入仓库')
            
            save_save(save)
            
            print(f'\n🎉 恭喜通关地牢三层！')
            print(f'获得灵魂碎片 {fragments}，累计 {save["fragments"]}')
            
            # 显示结局
            print('\n=== 你的旅程 ===')
            if hero.defeated_greed:
                print('🏆 隐藏成就：击败贪婪宝箱！')
            
            if hero.boss_kills == 0:
                print('🏃 "逃跑大师"')
                print('你成功通过了地牢，但没有击败任何一个Boss...')
                print('也许下次可以更勇敢一点？')
            elif hero.boss_kills <= 2:
                print('⚔️ "初出茅庐"')
                print(f'你击败了{hero.boss_kills}个Boss，展现出了不错的实力。')
                print('继续历练，你会变得更强！')
            elif hero.boss_kills == 3:
                print('👑 "地牢征服者"')
                print('你击败了所有Boss，证明了自己的实力！')
                print('但是否还有更强大的对手在等待着你？')
            elif hero.boss_kills >= 4:
                print('💎 "传说英雄"')
                print(f'你总共击败了{hero.boss_kills}个Boss，包括隐藏的贪婪宝箱！')
                print('你的名字将被永远铭记在地牢的历史上！')
            
            input('按 Enter 返回主菜单…')
            return

# ========================= 商店 =========================
def shop(save):
    prices = {'atk+5': 20, 'hp+20': 15, 'potion+1': 10}
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print('=== 商店 ===')
        print(f'你拥有灵魂碎片：{save["fragments"]}')
        for idx, (k, v) in enumerate(prices.items(), 1):
            level = save['shop'][k]
            print(f'{idx}) {k}（已{level}级）- {v} 碎片')
        print('0) 返回')
        choice = input('> ').strip()
        if choice == '0':
            return
        try:
            idx = int(choice)
            key = list(prices.keys())[idx - 1]
            cost = prices[key]
            if save['fragments'] >= cost:
                save['fragments'] -= cost
                save['shop'][key] += 1
                print(f'✔ 已购买 {key}！')
                save_save(save)
            else:
                print('❌ 碎片不足！')
            input('按 Enter 继续…')
        except (IndexError, ValueError):
            print('请输入正确编号')

if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        print('\n游戏被强制退出')