#!/usr/bin/env python3
"""
Quick test script for outbound calls.

Usage:
    python test.py
"""

import asyncio
import httpx
from rich.console import Console
from rich.table import Table

# ============================================================================
# CONFIGURATION - Edit these values
# ============================================================================

# Your phone number to call (E.164 format: +1234567890)
TO_NUMBER = "+573017063936"  # ⚠️ CHANGE THIS TO YOUR PHONE NUMBER

# API endpoint
API_URL = "http://localhost:5885"

# Optional: ElevenLabs voice ID for voice cloning
VOICE_ID = None  # Set to specific voice ID or leave None for default

# Optional: Custom room name (leave None for auto-generated)
ROOM_NAME = None

# Optional: Metadata to attach to the call
METADATA = {
    "test": True,
    "campaign": "test_campaign",
    "timestamp": None,  # Will be set automatically
}

# ============================================================================


console = Console()


async def test_outbound_call():
    """Make a test outbound call."""
    
    console.print("\n[bold cyan]🎙️  Metatron Outbound Call Test[/bold cyan]\n")
    
    # Add timestamp
    from datetime import datetime
    METADATA["timestamp"] = datetime.now().isoformat()
    
    # Prepare request
    request_data = {
        "phone_number": TO_NUMBER,
    }
    
    if ROOM_NAME:
        request_data["room_name"] = ROOM_NAME
    
    if METADATA:
        request_data["metadata"] = METADATA
    
    if VOICE_ID:
        request_data["voice_id"] = VOICE_ID
    
    # Display request info
    table = Table(title="Call Request")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Phone Number", TO_NUMBER)
    table.add_row("Room Name", ROOM_NAME or "[auto-generated]")
    table.add_row("Voice ID", VOICE_ID or "[default]")
    table.add_row("Metadata", str(METADATA))
    table.add_row("API Endpoint", f"{API_URL}/calls/outbound")
    
    console.print(table)
    console.print()
    
    try:
        console.print("[yellow]⏳ Initiating call...[/yellow]")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_URL}/calls/outbound",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                
                console.print("\n[bold green]✅ Call initiated successfully![/bold green]\n")
                
                # Display response
                result_table = Table(title="Call Details")
                result_table.add_column("Field", style="cyan")
                result_table.add_column("Value", style="green")
                
                result_table.add_row("Call ID", result["call_id"])
                result_table.add_row("Room Name", result["room_name"])
                result_table.add_row("Phone Number", result["phone_number"])
                result_table.add_row("Status", result["status"])
                
                console.print(result_table)
                
                console.print("\n[bold yellow]📞 The phone should be ringing now![/bold yellow]")
                console.print("[dim]Check your phone and answer the call to speak with the AI agent.[/dim]\n")
                
                # Instructions
                console.print("[bold]What to expect:[/bold]")
                console.print("1. Your phone will ring")
                console.print("2. Answer the call")
                console.print("3. Voice agent will greet you (outbound greeting)")
                console.print("4. Have a conversation with the AI sales agent")
                console.print("5. The agent will respond using ElevenLabs TTS\n")
                
                return result
                
            else:
                console.print(f"\n[bold red]❌ Error: HTTP {response.status_code}[/bold red]")
                console.print(f"[red]{response.text}[/red]\n")
                
                # Common errors
                if response.status_code == 503:
                    console.print("[yellow]💡 Troubleshooting:[/yellow]")
                    console.print("   • Make sure LIVEKIT_SIP_TRUNK_ID is set in .env")
                    console.print("   • Verify LiveKit credentials are configured")
                    console.print("   • Check that the API server is running\n")
                elif response.status_code == 400:
                    console.print("[yellow]💡 Troubleshooting:[/yellow]")
                    console.print("   • Check phone number format (must be E.164: +1234567890)")
                    console.print("   • Verify the number is valid\n")
                
                return None
                
    except httpx.ConnectError:
        console.print("\n[bold red]❌ Connection Error[/bold red]")
        console.print("[red]Cannot connect to API server[/red]\n")
        console.print("[yellow]💡 Make sure the API server is running:[/yellow]")
        console.print("   [dim]Terminal 1: uv run metatron api-server[/dim]\n")
        return None
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Unexpected Error[/bold red]")
        console.print(f"[red]{e}[/red]\n")
        return None


async def check_api_health():
    """Check if the API server is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_URL}/ping")
            if response.status_code == 200:
                data = response.json()
                
                # Show configuration status
                console.print("[bold]API Server Status:[/bold]")
                console.print(f"  ✅ Server is running")
                console.print(f"  LiveKit: {'✅' if data.get('livekit_configured') else '❌'}")
                console.print(f"  OpenAI: {'✅' if data.get('openai_configured') else '❌'}")
                console.print(f"  ElevenLabs: {'✅' if data.get('elevenlabs_configured') else '❌'}")
                console.print()
                
                if not data.get('livekit_configured'):
                    console.print("[yellow]⚠️  LiveKit not configured - outbound calls won't work[/yellow]\n")
                    return False
                
                return True
            else:
                console.print("[red]❌ API server responded with error[/red]\n")
                return False
                
    except httpx.ConnectError:
        console.print("[red]❌ Cannot connect to API server[/red]")
        console.print(f"[dim]Tried: {API_URL}/ping[/dim]\n")
        console.print("[yellow]Start the API server first:[/yellow]")
        console.print("   [dim]uv run metatron api-server[/dim]\n")
        return False
    except Exception as e:
        console.print(f"[red]Error checking API: {e}[/red]\n")
        return False


def main():
    """Main entry point."""
    
    # Validate configuration
    if TO_NUMBER == "+15551234567":
        console.print("\n[bold red]⚠️  WARNING: You need to change TO_NUMBER in test.py[/bold red]")
        console.print("[yellow]Edit the TO_NUMBER variable at the top of test.py[/yellow]")
        console.print("[dim]Example: TO_NUMBER = \"+14155551234\"[/dim]\n")
        return
    
    if not TO_NUMBER.startswith("+"):
        console.print("\n[bold red]❌ Invalid phone number format[/bold red]")
        console.print("[yellow]Phone number must be in E.164 format (start with +)[/yellow]")
        console.print(f"[dim]Your number: {TO_NUMBER}[/dim]")
        console.print(f"[dim]Correct format: +14155551234[/dim]\n")
        return
    
    # Run async tests
    async def run_tests():
        # Check API health first
        if not await check_api_health():
            console.print("[bold red]Please start the required services and try again.[/bold red]\n")
            return
        
        # Make the test call
        await test_outbound_call()
    
    asyncio.run(run_tests())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Test cancelled by user[/yellow]\n")
    except Exception as e:
        console.print(f"\n[bold red]Fatal error: {e}[/bold red]\n")

