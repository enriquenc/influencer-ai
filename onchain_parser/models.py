from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class TokenInfo:
    address: str
    symbol: str
    price: float
    volume24h: float
    liquidity: float
    priceChange24h: float

@dataclass
class TokenTransfer:
    token: TokenInfo
    from_address: str
    to_address: str
    amount: float
    operation: str  # 'BUY' or 'SELL'

    @property
    def total_value(self) -> Optional[float]:
        """Calculate total value in USD"""
        if self.token.price:
            return self.amount * self.token.price
        return None

    def format_amount(self) -> str:
        """Format amount with appropriate precision"""
        if self.amount >= 1000000:
            return f"{self.amount:,.0f}"
        elif self.amount >= 1:
            return f"{self.amount:,.2f}"
        else:
            return f"{self.amount:.8f}"

    @property
    def operation_emoji(self) -> str:
        """Get emoji for operation type"""
        return "🔴" if self.operation == "SELL" else "🟢"

@dataclass
class TransactionEvent:
    hash: str
    block_number: int
    timestamp: int
    from_address: str
    to_address: str
    value: float  # in ETH
    status: str
    transfers: List[TokenTransfer]

    @property
    def datetime(self) -> datetime:
        """Get datetime object from timestamp"""
        return datetime.fromtimestamp(self.timestamp)

    def format_full(self) -> str:
        """Format full transaction information"""
        output = [
            "═══════════════════════════════════════════════",
            "New Transaction:",
            "═══════════════════════════════════════════════",
            f"Time: {self.datetime}",
            f"Hash: {self.hash}",
            f"Block: {self.block_number}",
            f"Status: {self.status}",
            "",
            f"From: {self.from_address}",
            f"To: {self.to_address}",
            f"Value: {self.value} ETH",
            ""
        ]

        if self.transfers:
            output.extend([
                "Token Information:",
                "══════════════════════"
            ])

            for transfer in self.transfers:
                total_value_str = f"${transfer.total_value:.2f}" if transfer.total_value is not None else "No data"

                output.extend([
                    "",
                    f"{transfer.operation_emoji} Operation: {transfer.operation}",
                    f"Token: {transfer.token.symbol} ({transfer.token.address})",
                    f"└── Price: ${transfer.token.price:.4f}",
                    f"└── Price Change (24h): {transfer.token.priceChange24h}%",
                    f"└── Volume (24h): ${transfer.token.volume24h:,.2f}",
                    f"└── Liquidity: ${transfer.token.liquidity:,.2f}",
                    f"└── From: {transfer.from_address}",
                    f"└── To: {transfer.to_address}",
                    f"└── Amount: {transfer.format_amount()}",
                    f"└── Total Value: {total_value_str}",
                ])

        return "\n".join(output)

    def format_brief(self) -> str:
        """Format brief transaction info"""
        result = [
            f"Transaction detected at {datetime.fromtimestamp(self.timestamp)}:",
            f"Hash: {self.hash}",
            f"From: {self.from_address}",
            f"To: {self.to_address}",
            f"Value: {self.value} ETH"
        ]

        if self.transfers:
            transfer = self.transfers[0]
            result.extend([
                "",
                f"Token: {transfer.token.symbol}",
                f"Price: ${transfer.token.price:.4f}",
                f"Amount: {transfer.format_amount()}",
                f"Operation: {transfer.operation}"
            ])

        return "\n".join(result)