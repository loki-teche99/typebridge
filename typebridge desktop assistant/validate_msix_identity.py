"""
MSIX Identity Validator
Ensures that AppxManifest.xml matches the exact Microsoft Partner Center identity locking requirements.
"""
import sys
import xml.etree.ElementTree as ET

EXPECTED_NAME = "MadeByLokesh.Typebridge"
EXPECTED_PUBLISHER = "CN=9E9E696E-AFB3-4245-B9D4-E5822F2EDB0A"
EXPECTED_PUBLISHER_DISPLAY_NAME = "MadeByLokesh"
EXPECTED_STORE_ID = "9PL56S4CL4NW"
EXPECTED_PFN_PREFIX = "MadeByLokesh.Typebridge_"
EXPECTED_FULL_PFN = "MadeByLokesh.Typebridge_d4xnygzcj6ts8"

def validate_manifest(manifest_path: str):
    print(f"[*] Validating MSIX Manifest: {manifest_path}")
    tree = ET.parse(manifest_path)
    root = tree.getroot()

    # Namespace map
    ns = {
        'default': 'http://schemas.microsoft.com/appx/manifest/foundation/windows10',
        'uap': 'http://schemas.microsoft.com/appx/manifest/uap/windows10',
        'rescap': 'http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities'
    }

    identity = root.find('default:Identity', ns)
    if identity is None:
        identity = root.find('{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Identity')
    if identity is None:
        raise ValueError("FATAL: <Identity> element not found in manifest!")

    name = identity.attrib.get('Name')
    publisher = identity.attrib.get('Publisher')
    version = identity.attrib.get('Version')
    arch = identity.attrib.get('ProcessorArchitecture')

    print(f"    Name:                  {name}")
    print(f"    Publisher:             {publisher}")
    print(f"    Version:               {version}")
    print(f"    ProcessorArchitecture: {arch}")

    assert name == EXPECTED_NAME, f"Identity Name mismatch! Expected '{EXPECTED_NAME}', got '{name}'"
    assert publisher == EXPECTED_PUBLISHER, f"Identity Publisher mismatch! Expected '{EXPECTED_PUBLISHER}', got '{publisher}'"
    assert arch == "x64", f"ProcessorArchitecture must be x64, got '{arch}'"

    properties = root.find('default:Properties', ns)
    if properties is None:
        properties = root.find('{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Properties')
    if properties is not None:
        pub_display = properties.find('default:PublisherDisplayName', ns)
        if pub_display is None:
            pub_display = properties.find('{http://schemas.microsoft.com/appx/manifest/foundation/windows10}PublisherDisplayName')
        if pub_display is not None:
            assert pub_display.text == EXPECTED_PUBLISHER_DISPLAY_NAME, f"PublisherDisplayName mismatch! Expected '{EXPECTED_PUBLISHER_DISPLAY_NAME}', got '{pub_display.text}'"
            print(f"    PublisherDisplayName:  {pub_display.text}")

    print("\n[SUCCESS] Manifest strictly adheres to Microsoft Partner Center locked identity!")
    print(f"[SUCCESS] Target Package Family Name: {EXPECTED_FULL_PFN}")
    return True

if __name__ == "__main__":
    manifest_file = sys.argv[1] if len(sys.argv) > 1 else "msix/AppxManifest.xml"
    try:
        validate_manifest(manifest_file)
    except Exception as e:
        print(f"\n[FAILED] {e}", file=sys.stderr)
        sys.exit(1)
