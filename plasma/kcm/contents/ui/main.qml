import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils
import org.kde.plasma.plasma5support as P5Support

SimpleKCM {
    id: root

    Kirigami.FormLayout {
        anchors.fill: parent

        // --- ÚVODNÍ VYSVĚTLENÍ ---
        Kirigami.Separator {
            Kirigami.FormData.label: "Default Behavior"
            Kirigami.FormData.isSection: true
        }

        QQC2.Label {
            text: "Select how the secondary screen should behave permanently. This setting persists across reboots."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            Layout.maximumWidth: 600
        }

        // --- 1. AUTOMATICKÝ REŽIM (Doporučeno) ---
        QQC2.Button {
            text: "🤖 Automatic (Sensor Based)"
            icon.name: "input-tablet"
            Layout.fillWidth: true
            Layout.maximumWidth: 400
            onClicked: runCmd("automatic-enabled")

            Kirigami.FormData.label: "Standard:"
            QQC2.ToolTip.visible: hovered
            QQC2.ToolTip.text: "Screen turns on/off automatically when keyboard is removed/attached."
        }

        // --- 2. VŽDY ZAPNUTO (Desktop) ---
        QQC2.Button {
            text: "🖥 Always Extended (Force Dual)"
            icon.name: "view-dual"
            Layout.fillWidth: true
            Layout.maximumWidth: 400
            onClicked: runCmd("enforce-desktop")

            Kirigami.FormData.label: "Workstation:"
            QQC2.ToolTip.visible: hovered
            QQC2.ToolTip.text: "Both screens are always ON, ignoring the keyboard sensor."
        }

        // --- 3. VŽDY VYPNUTO (Cestování) ---
        QQC2.Button {
            text: "💻 Primary Screen Only"
            icon.name: "laptop"
            Layout.fillWidth: true
            Layout.maximumWidth: 400
            onClicked: runCmd("automatic-disabled")

            Kirigami.FormData.label: "Power Saving:"
            QQC2.ToolTip.visible: hovered
            QQC2.ToolTip.text: "Secondary screen is permanently disabled to save battery."
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
        }

        // --- ODKAZ NA POKROČILÉ NASTAVENÍ ---
        QQC2.Label {
            text: "Need to configure sensor sensitivity or specific hardware IDs?"
            font.italic: true
        }

        QQC2.Button {
            text: "Open Advanced Configuration"
            icon.name: "configure"
            onClicked: executable.connectSource("asus-screen-settings")
        }
    }

    // --- BACKEND LOGIKA ---
    function runCmd(mode) {
        var cmd = "dbus-send --session --dest=org.asus.ScreenToggle --type=method_call /org/asus/ScreenToggle org.asus.ScreenToggle.SetMode string:'" + mode + "'"
        executable.connectSource(cmd)
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            disconnectSource(sourceName)
        }
    }
}
