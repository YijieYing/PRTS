#!/bin/bash
exec "$(cd "$(dirname "$0")/.." && pwd)/interaction/bin/event" from-agentconsole
