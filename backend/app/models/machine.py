"""Machine model for arcade machine management"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, DECIMAL, Index
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class MachineType(str, enum.Enum):
    """Machine types"""
    GAME = "GAME"                     # Video games, arcade cabinets
    KIOSK = "KIOSK"                   # Card kiosks, ATMs
    ATTRACTION = "ATTRACTION"         # Rides, VR experiences
    VENDING = "VENDING"               # Prize machines, food/drink
    TOKEN_MACHINE = "TOKEN_MACHINE"   # Token exchange


class MachineStatus(str, enum.Enum):
    """Machine status"""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    RETIRED = "RETIRED"


class Machine(Base):
    """
    Machine model for arcade machines and devices.
    
    Each machine can process card transactions and report status.
    """
    __tablename__ = "machines"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Location
    location_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Machine details
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True, unique=True, index=True)
    serial_number = Column(String(100), nullable=True, unique=True)

    # Type and status
    machine_type = Column(
        String(50),
        nullable=False,
        default=MachineType.GAME,
        index=True
    )
    status = Column(
        String(20),
        nullable=False,
        default=MachineStatus.OFFLINE,
        index=True
    )

    # Pricing
    cost_per_play = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    currency = Column(String(10), default='EGP')

    # Revenue tracking
    revenue_total = Column(DECIMAL(12, 2), nullable=False, default=0.00)
    revenue_today = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    plays_today = Column(String(50), nullable=False, default='0')

    # Usage tracking
    total_plays = Column(String(50), nullable=False, default='0')
    last_played = Column(DateTime(timezone=True), nullable=True)

    # Maintenance
    last_maintenance = Column(DateTime(timezone=True), nullable=True)
    next_maintenance = Column(DateTime(timezone=True), nullable=True)
    maintenance_notes = Column(String(500), nullable=True)

    # Network/Device info
    ip_address = Column(String(50), nullable=True)
    mac_address = Column(String(50), nullable=True)
    firmware_version = Column(String(50), nullable=True)

    # Metadata
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    installed_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_machines_location', 'location_id'),
        Index('idx_machines_type', 'machine_type'),
        Index('idx_machines_status', 'status'),
        Index('idx_machines_code', 'code'),
    )

    def __repr__(self):
        return f"<Machine(id={self.id}, name={self.name}, status={self.status})>"

    @property
    def is_online(self):
        """Check if machine is online"""
        return self.status == MachineStatus.ONLINE

    @property
    def needs_maintenance(self):
        """Check if machine needs maintenance"""
        if self.next_maintenance and datetime.utcnow() >= self.next_maintenance:
            return True
        return self.status in [MachineStatus.MAINTENANCE, MachineStatus.OUT_OF_ORDER]

    @property
    def days_since_maintenance(self):
        """Days since last maintenance"""
        if not self.last_maintenance:
            return 999  # Never maintained
        delta = datetime.utcnow() - self.last_maintenance
        return delta.days

    def go_online(self):
        """Mark machine as online"""
        self.status = MachineStatus.ONLINE
        self.updated_at = datetime.utcnow()

    def go_offline(self):
        """Mark machine as offline"""
        self.status = MachineStatus.OFFLINE
        self.updated_at = datetime.utcnow()

    def set_maintenance(self, notes=None):
        """Set machine to maintenance mode"""
        self.status = MachineStatus.MAINTENANCE
        self.last_maintenance = datetime.utcnow()
        if notes:
            self.maintenance_notes = notes
        self.updated_at = datetime.utcnow()

    def schedule_maintenance(self, days_ahead=30):
        """Schedule next maintenance"""
        self.next_maintenance = datetime.utcnow() + timedelta(days=days_ahead)
        self.updated_at = datetime.utcnow()

    def record_play(self, amount):
        """Record a play and update revenue"""
        self.revenue_total += amount
        self.revenue_today += amount
        self.total_plays = str(int(self.total_plays) + 1)
        self.plays_today = str(int(self.plays_today) + 1)
        self.last_played = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def reset_daily_stats(self):
        """Reset daily stats (call at start of day)"""
        self.revenue_today = 0.00
        self.plays_today = '0'
        self.updated_at = datetime.utcnow()