# Architecture

GlowLink has four logical layers. This makes it possible to change the interface or a system
adapter without spreading BLE details through the project.

1. **CLI, GUI, and Web UI** accept input, show state, and contain no BLE logic.
2. **Application scenarios** coordinate discovery, selection, connection, colour, and sync. They
   accept application-level data and return results for an interface.
3. **BLE and protocol domain** builds frames, owns compatibility rules, and manages the session.
4. **System adapters** connect the application to Bleak/WinRT, pywebview, mss, and the file
   system.

Dependencies point downward only: UI → scenarios → domain → adapters. A lower layer does not
import a higher one; `protocol.py` does not depend on Bleak, the UI, or Windows. The UI does not
create `BleakClient`, call GATT operations, or interpret UUIDs: those details remain at the BLE
boundary and reach an interface only as a prepared result.

Current scenarios may live next to their entry point. A new scenario shared by two interfaces
belongs in an application module, rather than being duplicated in CLI and GUI. Decisions that
change these boundaries are recorded as [ADRs](decisions/README.md).
