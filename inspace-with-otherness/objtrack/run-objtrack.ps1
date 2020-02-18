Set-StrictMode -Version 3

$processingJava = "C:\Users\inspacepc\Downloads\processing-3.5.3-windows64\processing-3.5.3\processing-java.exe"
$sketchDir = "C:\Users\inspacepc\objtrack"

While($true) {
    Start-Process -Wait -NoNewWindow $processingJava "--sketch=$sketchDir","--run"
    Start-Sleep 2
}