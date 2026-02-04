#!/usr/bin/env python3
"""
PWR-STD-04 Professional Documentation Generator

Enterprise-grade documentation generator for PWR-STD-04 test results.
Creates comprehensive Word documents with professional formatting,
charts, tables, and detailed analysis.

Author: Senior Test Automation Engineer  
Version: 1.0.0 - Production Grade
Date: 2024-12-03
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

# Node.js docx generation script
DOCX_GENERATOR_SCRIPT = '''
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
        Header, Footer, AlignmentType, WidthType, ShadingType, BorderStyle,
        HeadingLevel, LevelFormat, PageBreak } = require('docx');
const fs = require('fs');

// Read the JSON data
const resultsData = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const outputFile = process.argv[3];

// Professional styling
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

// Create the document
const doc = new Document({
  styles: {
    default: { 
      document: { 
        run: { font: "Arial", size: 24 } // 12pt default
      } 
    },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "2B2B2B" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 }
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2B2B2B" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 }
      },
      {
        id: "Heading3",
        name: "Heading 3",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2B2B2B" },
        paragraph: { spacing: { before: 120, after: 120 }, outlineLevel: 2 }
      }
    ]
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0,
          format: LevelFormat.BULLET,
          text: "•",
          alignment: AlignmentType.LEFT,
          style: {
            paragraph: {
              indent: { left: 720, hanging: 360 }
            }
          }
        }]
      }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: {
          width: 12240,   // US Letter
          height: 15840
        },
        margin: { 
          top: 1440, 
          right: 1440, 
          bottom: 1440, 
          left: 1440 
        }
      }
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({
                text: "PWR-STD-04 Steady-State Rail Verification Report",
                font: "Arial",
                size: 20,
                color: "666666"
              })
            ]
          })
        ]
      })
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({
                text: `Generated: ${new Date().toLocaleString()} | Page `,
                font: "Arial",
                size: 18,
                color: "666666"
              })
            ]
          })
        ]
      })
    },
    children: generateDocumentContent(resultsData)
  }]
});

function generateDocumentContent(data) {
  const content = [];
  const testInfo = data.test_info;
  const measurements = data.measurements;
  const specifications = data.specifications;
  
  // Title Page
  content.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 1440, after: 720 },
      children: [
        new TextRun({
          text: "PWR-STD-04",
          font: "Arial",
          size: 48,
          bold: true,
          color: "1F4788"
        })
      ]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 360 },
      children: [
        new TextRun({
          text: "Steady-State Rail Verification",
          font: "Arial",
          size: 36,
          bold: true,
          color: "2B2B2B"
        })
      ]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 720 },
      children: [
        new TextRun({
          text: "Automated Test Report",
          font: "Arial",
          size: 28,
          color: "666666"
        })
      ]
    })
  );
  
  // Test Summary Box
  const overallStatus = testInfo.overall_result;
  const statusColor = overallStatus === 'PASS' ? '2E7D32' : 
                     overallStatus === 'FAIL' ? 'C62828' : '757575';
  
  content.push(
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      columnWidths: [9360],
      rows: [
        new TableRow({
          children: [
            new TableCell({
              borders,
              width: { size: 9360, type: WidthType.DXA },
              shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
              margins: { top: 240, bottom: 240, left: 360, right: 360 },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  spacing: { after: 120 },
                  children: [
                    new TextRun({
                      text: "TEST RESULT",
                      font: "Arial",
                      size: 24,
                      bold: true,
                      color: "2B2B2B"
                    })
                  ]
                }),
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [
                    new TextRun({
                      text: overallStatus,
                      font: "Arial",
                      size: 40,
                      bold: true,
                      color: statusColor
                    })
                  ]
                })
              ]
            })
          ]
        })
      ]
    }),
    new Paragraph({ children: [new TextRun("")] }) // Spacing
  );
  
  // Page break
  content.push(new Paragraph({ children: [new PageBreak()] }));
  
  // Executive Summary
  content.push(
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun("Executive Summary")]
    })
  );
  
  const testStartTime = new Date(testInfo.test_start_time).toLocaleString();
  const testEndTime = new Date(testInfo.test_end_time).toLocaleString();
  const testDuration = ((new Date(testInfo.test_end_time) - new Date(testInfo.test_start_time)) / 1000).toFixed(1);
  
  content.push(
    new Paragraph({
      children: [
        new TextRun({
          text: "This report presents the results of PWR-STD-04 steady-state rail verification testing performed on the CPU board power distribution network. The test validates that all power rails reach and maintain correct DC voltage levels under nominal input conditions."
        })
      ]
    }),
    new Paragraph({ children: [new TextRun("")] }),
    
    // Test Information Table
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      columnWidths: [3120, 6240],
      rows: [
        new TableRow({
          children: [
            new TableCell({
              borders,
              width: { size: 3120, type: WidthType.DXA },
              shading: { fill: "E3F2FD", type: ShadingType.CLEAR },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: "Test Name", bold: true })] })]
            }),
            new TableCell({
              borders,
              width: { size: 6240, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: testInfo.test_name })] })]
            })
          ]
        }),
        new TableRow({
          children: [
            new TableCell({
              borders,
              width: { size: 3120, type: WidthType.DXA },
              shading: { fill: "E3F2FD", type: ShadingType.CLEAR },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: "Start Time", bold: true })] })]
            }),
            new TableCell({
              borders,
              width: { size: 6240, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: testStartTime })] })]
            })
          ]
        }),
        new TableRow({
          children: [
            new TableCell({
              borders,
              width: { size: 3120, type: WidthType.DXA },
              shading: { fill: "E3F2FD", type: ShadingType.CLEAR },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: "End Time", bold: true })] })]
            }),
            new TableCell({
              borders,
              width: { size: 6240, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: testEndTime })] })]
            })
          ]
        }),
        new TableRow({
          children: [
            new TableCell({
              borders,
              width: { size: 3120, type: WidthType.DXA },
              shading: { fill: "E3F2FD", type: ShadingType.CLEAR },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: "Duration", bold: true })] })]
            }),
            new TableCell({
              borders,
              width: { size: 6240, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: testDuration + " seconds" })] })]
            })
          ]
        }),
        new TableRow({
          children: [
            new TableCell({
              borders,
              width: { size: 3120, type: WidthType.DXA },
              shading: { fill: "E3F2FD", type: ShadingType.CLEAR },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [new Paragraph({ children: [new TextRun({ text: "Overall Result", bold: true })] })]
            }),
            new TableCell({
              borders,
              width: { size: 6240, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 180, right: 180 },
              children: [
                new Paragraph({ 
                  children: [
                    new TextRun({ 
                      text: overallStatus, 
                      bold: true, 
                      color: statusColor 
                    })
                  ] 
                })
              ]
            })
          ]
        })
      ]
    })
  );
  
  // Detailed Results Section
  content.push(
    new Paragraph({ children: [new TextRun("")] }),
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun("Detailed Test Results")]
    })
  );
  
  // Results Table Header
  const resultsTableRows = [
    new TableRow({
      children: [
        new TableCell({
          borders,
          width: { size: 1400, type: WidthType.DXA },
          shading: { fill: "1976D2", type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 120, right: 120 },
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Rail", bold: true, color: "FFFFFF" })] 
          })]
        }),
        new TableCell({
          borders,
          width: { size: 1200, type: WidthType.DXA },
          shading: { fill: "1976D2", type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 120, right: 120 },
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Test Point", bold: true, color: "FFFFFF" })] 
          })]
        }),
        new TableCell({
          borders,
          width: { size: 1400, type: WidthType.DXA },
          shading: { fill: "1976D2", type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 120, right: 120 },
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Measured", bold: true, color: "FFFFFF" })] 
          })]
        }),
        new TableCell({
          borders,
          width: { size: 1800, type: WidthType.DXA },
          shading: { fill: "1976D2", type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 120, right: 120 },
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Specification", bold: true, color: "FFFFFF" })] 
          })]
        }),
        new TableCell({
          borders,
          width: { size: 1200, type: WidthType.DXA },
          shading: { fill: "1976D2", type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 120, right: 120 },
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Deviation", bold: true, color: "FFFFFF" })] 
          })]
        }),
        new TableCell({
          borders,
          width: { size: 1000, type: WidthType.DXA },
          shading: { fill: "1976D2", type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 120, right: 120 },
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Status", bold: true, color: "FFFFFF" })] 
          })]
        }),
        new TableCell({
          borders,
          width: { size: 1360, type: WidthType.DXA },
          shading: { fill: "1976D2", type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 120, right: 120 },
          children: [new Paragraph({ 
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Std Dev", bold: true, color: "FFFFFF" })] 
          })]
        })
      ]
    })
  ];
  
  // Add measurement rows
  const railOrder = ['5V_INPUT', '3V6', '3V3', '2V5', '1V8', '1V35'];
  
  railOrder.forEach(railId => {
    if (measurements[railId] && specifications[railId]) {
      const meas = measurements[railId];
      const spec = specifications[railId];
      
      const statusColor = meas.status === 'IN_TOLERANCE' ? '2E7D32' : 'C62828';
      const rowColor = meas.status === 'IN_TOLERANCE' ? 'E8F5E8' : 'FFEBEE';
      
      resultsTableRows.push(
        new TableRow({
          children: [
            new TableCell({
              borders,
              width: { size: 1400, type: WidthType.DXA },
              shading: { fill: rowColor, type: ShadingType.CLEAR },
              margins: { top: 120, bottom: 120, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: meas.rail_name, bold: true })] })]
            }),
            new TableCell({
              borders,
              width: { size: 1200, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 120, right: 120 },
              children: [new Paragraph({ 
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: meas.test_point })] 
              })]
            }),
            new TableCell({
              borders,
              width: { size: 1400, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 120, right: 120 },
              children: [new Paragraph({ 
                alignment: AlignmentType.RIGHT,
                children: [new TextRun({ text: meas.measured_voltage.toFixed(4) + "V" })] 
              })]
            }),
            new TableCell({
              borders,
              width: { size: 1800, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 120, right: 120 },
              children: [new Paragraph({ 
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: spec.min_voltage.toFixed(3) + "V - " + spec.max_voltage.toFixed(3) + "V" })] 
              })]
            }),
            new TableCell({
              borders,
              width: { size: 1200, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 120, right: 120 },
              children: [new Paragraph({ 
                alignment: AlignmentType.RIGHT,
                children: [new TextRun({ text: (meas.deviation_percent >= 0 ? "+" : "") + meas.deviation_percent.toFixed(2) + "%" })] 
              })]
            }),
            new TableCell({
              borders,
              width: { size: 1000, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 120, right: 120 },
              children: [new Paragraph({ 
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ 
                  text: meas.status === 'IN_TOLERANCE' ? 'PASS' : 'FAIL', 
                  bold: true, 
                  color: statusColor 
                })] 
              })]
            }),
            new TableCell({
              borders,
              width: { size: 1360, type: WidthType.DXA },
              margins: { top: 120, bottom: 120, left: 120, right: 120 },
              children: [new Paragraph({ 
                alignment: AlignmentType.RIGHT,
                children: [new TextRun({ text: meas.voltage_std_dev ? meas.voltage_std_dev.toFixed(6) + "V" : "N/A" })] 
              })]
            })
          ]
        })
      );
    }
  });
  
  content.push(
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      columnWidths: [1400, 1200, 1400, 1800, 1200, 1000, 1360],
      rows: resultsTableRows
    })
  );
  
  // Test Configuration Section
  content.push(
    new Paragraph({ children: [new TextRun("")] }),
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun("Test Configuration")]
    })
  );
  
  const config = testInfo.configuration;
  content.push(
    new Paragraph({
      numbering: { reference: "bullets", level: 0 },
      children: [new TextRun("PSU Voltage: " + config.psu_voltage + "V")]
    }),
    new Paragraph({
      numbering: { reference: "bullets", level: 0 },
      children: [new TextRun("PSU Current Limit: " + config.psu_current_limit + "A")]
    }),
    new Paragraph({
      numbering: { reference: "bullets", level: 0 },
      children: [new TextRun("Stabilization Time: " + config.stabilization_time + " seconds")]
    }),
    new Paragraph({
      numbering: { reference: "bullets", level: 0 },
      children: [new TextRun("Measurement Samples: " + config.measurement_samples + " per rail")]
    }),
    new Paragraph({
      numbering: { reference: "bullets", level: 0 },
      children: [new TextRun("Measurement Interval: " + config.measurement_interval + " seconds")]
    })
  );
  
  // Footer
  content.push(
    new Paragraph({ children: [new PageBreak()] }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 720 },
      children: [
        new TextRun({
          text: "End of Report",
          font: "Arial",
          size: 24,
          italic: true,
          color: "666666"
        })
      ]
    })
  );
  
  return content;
}

// Generate and save the document
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputFile, buffer);
  console.log(`Professional test report generated: ${outputFile}`);
}).catch(error => {
  console.error('Error generating document:', error);
  process.exit(1);
});
'''


class PWRStd04DocumentGenerator:
    """
    Professional documentation generator for PWR-STD-04 test results
    
    Creates comprehensive Word documents with professional formatting,
    detailed analysis, and enterprise-grade presentation.
    """
    
    def __init__(self, output_directory: str):
        """
        Initialize documentation generator
        
        Args:
            output_directory: Directory for output files
        """
        self.output_dir = Path(output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger(f'{self.__class__.__name__}')
    
    def generate_professional_report(self, 
                                   json_results_file: str, 
                                   output_filename: Optional[str] = None) -> str:
        """
        Generate comprehensive Word document from JSON test results
        
        Args:
            json_results_file: Path to JSON results file
            output_filename: Optional custom output filename
            
        Returns:
            str: Path to generated document
        """
        try:
            # Validate input file exists
            json_path = Path(json_results_file)
            if not json_path.exists():
                raise FileNotFoundError(f"JSON results file not found: {json_results_file}")
            
            # Generate output filename if not provided
            if output_filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"PWR_STD_04_Report_{timestamp}.docx"
            
            output_path = self.output_dir / output_filename
            
            # Create temporary script file
            script_path = self.output_dir / "generate_report.js"
            with open(script_path, 'w') as f:
                f.write(DOCX_GENERATOR_SCRIPT)
            
            self._logger.info(f"Generating professional Word document: {output_path}")
            
            # Install docx package if needed
            install_cmd = "npm install docx"
            install_result = os.system(install_cmd)
            if install_result != 0:
                self._logger.warning("Failed to install docx package, may already be installed")
            
            # Run Node.js script to generate document
            cmd = f"node {script_path} {json_path} {output_path}"
            result = os.system(cmd)
            
            if result != 0:
                raise RuntimeError(f"Document generation failed with exit code: {result}")
            
            # Cleanup temporary script
            try:
                os.remove(script_path)
            except:
                pass  # Ignore cleanup errors
            
            self._logger.info(f"Professional report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self._logger.error(f"Failed to generate professional report: {e}")
            raise
    
    def generate_quick_summary(self, json_results_file: str) -> str:
        """
        Generate a quick text summary from JSON results
        
        Args:
            json_results_file: Path to JSON results file
            
        Returns:
            str: Formatted summary text
        """
        try:
            with open(json_results_file, 'r') as f:
                data = json.load(f)
            
            test_info = data['test_info']
            measurements = data['measurements']
            
            summary = []
            summary.append("=" * 60)
            summary.append("PWR-STD-04 QUICK SUMMARY")
            summary.append("=" * 60)
            summary.append(f"Overall Result: {test_info['overall_result']}")
            summary.append(f"Test Duration: {((datetime.fromisoformat(test_info['test_end_time'].replace('Z', '+00:00')) - datetime.fromisoformat(test_info['test_start_time'].replace('Z', '+00:00'))).total_seconds()):.1f} seconds")
            summary.append("")
            
            summary.append("RAIL RESULTS:")
            for rail_id, meas in measurements.items():
                status_symbol = "[PASS]" if meas['status'] == 'IN_TOLERANCE' else "[FAIL]"
                summary.append(f"{status_symbol} {meas['rail_name']}: {meas['measured_voltage']:.4f}V ({meas['deviation_percent']:+.2f}%)")
            
            return "\n".join(summary)
            
        except Exception as e:
            self._logger.error(f"Failed to generate quick summary: {e}")
            return f"Error generating summary: {e}"


# Integration function for main test class
def add_documentation_to_test_class():
    """
    Add the documentation generation method to the main test class
    This would be integrated into the PWRStd04SteadyStateTest class
    """
    
    def generate_test_documentation(self):
        """Generate professional Word document with test results"""
        if not self._test_start_time:
            self._logger.warning("Cannot generate documentation - test not completed")
            return
        
        try:
            # Find the most recent JSON results file
            timestamp = self._test_start_time.strftime('%Y%m%d_%H%M%S')
            json_file = self._output_dir / f"pwr_std_04_results_{timestamp}.json"
            
            if not json_file.exists():
                self._logger.error(f"JSON results file not found: {json_file}")
                return
            
            # Create documentation generator
            doc_generator = PWRStd04DocumentGenerator(str(self._output_dir))
            
            # Generate professional Word document
            doc_path = doc_generator.generate_professional_report(
                str(json_file),
                f"PWR_STD_04_Professional_Report_{timestamp}.docx"
            )
            
            self._logger.info(f"Professional documentation generated: {doc_path}")
            
            # Generate quick summary
            summary = doc_generator.generate_quick_summary(str(json_file))
            summary_file = self._output_dir / f"pwr_std_04_quick_summary_{timestamp}.txt"
            
            with open(summary_file, 'w') as f:
                f.write(summary)
            
            self._logger.info(f"Quick summary generated: {summary_file}")
            
        except Exception as e:
            self._logger.error(f"Documentation generation failed: {e}")
    
    # This method would be added to the PWRStd04SteadyStateTest class
    return generate_test_documentation


if __name__ == "__main__":
    """Test the documentation generator"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python pwr_std_04_documentation.py <json_results_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    # Create documentation generator
    doc_gen = PWRStd04DocumentGenerator("./test_docs")
    
    # Generate professional report
    try:
        doc_path = doc_gen.generate_professional_report(json_file)
        print(f"Professional report generated: {doc_path}")
        
        # Generate quick summary
        summary = doc_gen.generate_quick_summary(json_file)
        print("\n" + summary)
        
    except Exception as e:
        print(f"Documentation generation failed: {e}")
        sys.exit(1)
