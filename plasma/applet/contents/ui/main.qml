import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.components 3.0 as PlasmaComponents3
import org.kde.plasma.plasma5support as P5Support

PlasmoidItem {
    id: root

    // Zvětšíme výšku pro více tlačítek
    width: 320
    height: 450

    Plasmoid.icon: "input-tablet"
    Plasmoid.title: "Asus Presentation"

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // --- Hlavička ---
        PlasmaComponents3.Label {
            text: "Presentation Mode"
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 10
        }

        // --- Tlačítko RESET ---
        // Slouží k ukončení dočasného režimu a návratu k automatice
        PlasmaComponents3.Button {
            text: "⏹ Stop (Automatic)"
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            onClicked: runCmd("automatic-enabled")
        }

        // Oddělovač
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "gray"
            opacity: 0.3
        }

        // --- Mřížka dočasných režimů ---
        GridLayout {
            columns: 2
            Layout.fillWidth: true
            rowSpacing: 8
            columnSpacing: 8

            // 1. Řádek: Zrcadlení
            PlasmaComponents3.Button {
                text: "🪞 Mirror"
                Layout.fillWidth: true
                onClicked: runCmd("temp-mirror")
            }
            PlasmaComponents3.Button {
                text: "🙃 Reverse"
                Layout.fillWidth: true
                onClicked: runCmd("temp-reverse-mirror")
            }

            // 2. Řádek: Rozšířená plocha
            PlasmaComponents3.Button {
                text: "🖥 Extend"
                Layout.fillWidth: true
                onClicked: runCmd("temp-desktop")
            }
            PlasmaComponents3.Button {
                text: "🔄 Rotated"
                Layout.fillWidth: true
                onClicked: runCmd("temp-rotated-desktop")
            }

            // 3. Řádek: Jednotlivé displeje (dočasně)
            PlasmaComponents3.Button {
                text: "⬆ Top Only"
                Layout.fillWidth: true
                onClicked: runCmd("temp-primary-only")
            }
            PlasmaComponents3.Button {
                text: "⬇ Btm Only"
                Layout.fillWidth: true
                onClicked: runCmd("temp-secondary-only")
            }
        }

        // --- Patička ---
        Item { Layout.fillHeight: true } // Pružná mezera

        PlasmaComponents3.Button {
            text: "⚙️ Advanced Settings"
            Layout.fillWidth: true
            onClicked: {
                executable.connectSource("asus-screen-settings")
                root.expanded = false
            }
        }
    }

    // --- Logika ---
    function runCmd(mode) {
        var cmd = "dbus-send --session --dest=org.asus.ScreenToggle --type=method_call /org/asus/ScreenToggle org.asus.ScreenToggle.SetMode string:'" + mode + "'"
        executable.connectSource(cmd)
        root.expanded = false
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: {
            disconnectSource(sourceName)
        }
    }
}
