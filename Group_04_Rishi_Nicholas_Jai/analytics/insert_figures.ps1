$docPath = "C:\Users\Rishi Koli\Downloads\Main\Main\Group_04_Rishi_Nicholas_Jai\docs\MDRIIA_Group_04_Technical_Dossier.docx"
$pdfPath = "C:\Users\Rishi Koli\Downloads\Main\Main\Group_04_Rishi_Nicholas_Jai\docs\MDRIIA_Group_04_Technical_Dossier.pdf"
$figDir = "C:\Users\Rishi Koli\Downloads\Main\Main\Group_04_Rishi_Nicholas_Jai\docs\figures"

$replacements = @(
    @{ Placeholder = "[ Sensitivity graph: P_payback / NCRI vs the uncertain input ]"; Image = "$figDir\graph_sensitivity_ncri.png"; Width = 230 },
    @{ Placeholder = "[ Queuing graph: W_q vs utilisation ρ, or labour-reallocation chart ]"; Image = "$figDir\graph_queuing_delay.png"; Width = 230 },
    @{ Placeholder = "[ Trajectory plot: reference vs actual, one representative run ]"; Image = "$figDir\graph_trajectory_tracking.png"; Width = 230 },
    @{ Placeholder = "[ Box-plot of the primary metric: baseline vs proposed, N runs each ]"; Image = "$figDir\graph_boxplot_force.png"; Width = 220 }
)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($docPath)
    
    foreach ($item in $replacements) {
        $findText = $item.Placeholder
        $imgPath = $item.Image
        $w = $item.Width

        $range = $doc.Content
        $find = $range.Find
        $find.ClearFormatting()
        $find.Text = $findText
        $find.Forward = $true
        $find.Wrap = 0 # wdFindStop

        if ($find.Execute()) {
            Write-Host "Found placeholder: $findText"
            # Delete placeholder text
            $range.Text = ""
            # Insert picture at this range
            $shape = $range.InlineShapes.AddPicture($imgPath, $false, $true)
            $shape.Width = $w
            Write-Host "Successfully inserted image: $imgPath"
        } else {
            Write-Host "Placeholder not found: $findText"
        }
    }

    $doc.Save()
    Write-Host "Document saved."

    # Export to PDF
    $doc.ExportAsFixedFormat($pdfPath, 17) # 17 = wdExportFormatPDF
    Write-Host "PDF re-exported to: $pdfPath"
} finally {
    if ($doc) { $doc.Close($false) }
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}