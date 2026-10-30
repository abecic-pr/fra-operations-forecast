import Foundation
import CoreText
import CoreGraphics
let args = CommandLine.arguments
let label = args[1]
let face = args[2]
let size = Double(args[3])!
let x = Double(args[4])!
let y = Double(args[5])!
let font = CTFontCreateWithName(face as CFString, size, nil)
let attr = NSAttributedString(string: label, attributes: [NSAttributedString.Key(kCTFontAttributeName as String): font])
let line = CTLineCreateWithAttributedString(attr)
var paths: [String] = []
func n(_ a: CGFloat) -> String { String(format:"%.3f", Double(a)) }
for run in CTLineGetGlyphRuns(line) as! [CTRun] {
 let count = CTRunGetGlyphCount(run)
 var glyphs = [CGGlyph](repeating:0,count:count)
 var points = [CGPoint](repeating:.zero,count:count)
 CTRunGetGlyphs(run, CFRangeMake(0,0), &glyphs)
 CTRunGetPositions(run, CFRangeMake(0,0), &points)
 for i in 0..<count {
  var tr = CGAffineTransform(a:1,b:0,c:0,d:-1,tx:x+Double(points[i].x),ty:y-Double(points[i].y))
  if let path = CTFontCreatePathForGlyph(font,glyphs[i],&tr) {
   var d = ""
   path.applyWithBlock { ep in
    let e=ep.pointee, p=e.points
    switch e.type {
    case .moveToPoint: d += "M\(n(p[0].x)) \(n(p[0].y))"
    case .addLineToPoint: d += "L\(n(p[0].x)) \(n(p[0].y))"
    case .addQuadCurveToPoint: d += "Q\(n(p[0].x)) \(n(p[0].y)) \(n(p[1].x)) \(n(p[1].y))"
    case .addCurveToPoint: d += "C\(n(p[0].x)) \(n(p[0].y)) \(n(p[1].x)) \(n(p[1].y)) \(n(p[2].x)) \(n(p[2].y))"
    case .closeSubpath: d += "Z"
    @unknown default: break
    }
   }
   paths.append("<path d=\"\(d)\"/>")
  }
 }
}
print(paths.joined(separator:"\n"))
