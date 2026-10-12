package com.typebridge.mobile.utils

import java.util.regex.Pattern

/**
 * TypeBridge Mobile - Java Code Structure & Indentation Engine
 *
 * Sanitizes and formats Java source code with mathematical 4-space precision.
 * Eliminates extra spaces from line 1 (paste pad offsets), replaces non-breaking spaces (\u00A0)
 * and smart quotes, and formats blocks ({ ... }) cleanly.
 */
object JavaCodeFormatter {

    private val UNICODE_SPACES: Pattern = Pattern.compile("[\u00A0\u2000-\u200B\u202F\u205F\u3000\uFEFF]")
    private val SMART_DOUBLE_QUOTES: Pattern = Pattern.compile("[\u201C\u201D\u201E\u201F\u00AB\u00BB]")
    private val SMART_SINGLE_QUOTES: Pattern = Pattern.compile("[\u2018\u2019\u201A\u201B]")

    fun sanitize(text: String): String {
        if (text.isEmpty()) return ""

        var clean = text.replace("\r\n", "\n").replace("\r", "\n")
        clean = UNICODE_SPACES.matcher(clean).replaceAll(" ")
        clean = SMART_DOUBLE_QUOTES.matcher(clean).replaceAll("\"")
        clean = SMART_SINGLE_QUOTES.matcher(clean).replaceAll("'")
        clean = clean.replace("\t", "    ")
        return clean
    }

    fun stripLeadingMargins(text: String): String {
        val clean = sanitize(text)
        val lines = clean.split("\n")
        if (lines.isEmpty()) return ""

        var firstNonEmptyIdx = -1
        var firstLineIndent = 0

        for (i in lines.indices) {
            val stripped = lines[i].trimStart(' ')
            if (stripped.isNotEmpty()) {
                firstNonEmptyIdx = i
                firstLineIndent = lines[i].length - stripped.length
                break
            }
        }

        if (firstNonEmptyIdx == -1) return clean

        var minIndent = Int.MAX_VALUE
        for (l in lines) {
            if (l.trim().isNotEmpty()) {
                val ind = l.length - l.trimStart(' ').length
                if (ind < minIndent) minIndent = ind
            }
        }
        if (minIndent == Int.MAX_VALUE) minIndent = 0

        val firstStripped = lines[firstNonEmptyIdx].trim()
        val isJavaRoot = listOf(
            "package", "import", "public class", "class", "public interface",
            "interface", "public enum", "enum", "public record", "record", "@", "/*"
        ).any { firstStripped.startsWith(it) }

        val dedentAmount = if (isJavaRoot) firstLineIndent else minIndent

        val outLines = ArrayList<String>(lines.size)
        for (l in lines) {
            if (l.trim().isEmpty()) {
                outLines.add("")
            } else {
                val currentIndent = l.length - l.trimStart(' ').length
                val stripCount = minOf(dedentAmount, currentIndent)
                outLines.add(l.substring(stripCount))
            }
        }

        return outLines.joinToString("\n")
    }

    data class BraceAnalysis(
        val openB: Int,
        val closeB: Int,
        val startsWithClose: Boolean,
        val inBlockComment: Boolean
    )

    fun countEffectiveBraces(line: String, inBlockComment: Boolean = false): BraceAnalysis {
        var openB = 0
        var closeB = 0
        var inString = false
        var inChar = false
        var escaped = false
        var firstEffectiveChar = ' '
        var inBlock = inBlockComment

        var i = 0
        val n = line.length
        while (i < n) {
            val c = line[i]

            // Inside multi-line block comment /* ... */
            if (inBlock) {
                if (c == '*' && i + 1 < n && line[i + 1] == '/') {
                    inBlock = false
                    i += 2
                    continue
                }
                i++
                continue
            }

            // Inside string literal "..."
            if (inString) {
                if (escaped) {
                    escaped = false
                    i++
                    continue
                }
                if (c == '\\') {
                    escaped = true
                    i++
                    continue
                }
                if (c == '"') {
                    inString = false
                    i++
                    continue
                }
                i++
                continue
            }

            // Inside char literal '...'
            if (inChar) {
                if (escaped) {
                    escaped = false
                    i++
                    continue
                }
                if (c == '\\') {
                    escaped = true
                    i++
                    continue
                }
                if (c == '\'') {
                    inChar = false
                    i++
                    continue
                }
                i++
                continue
            }

            // Normal code outside comments and strings
            if (c == '/' && i + 1 < n) {
                val nextC = line[i + 1]
                if (nextC == '/') {
                    // Single-line comment //: rest of line is a comment
                    break
                } else if (nextC == '*') {
                    // Start of block comment /*
                    inBlock = true
                    i += 2
                    continue
                }
            }

            if (c == '"') {
                inString = true
                i++
                continue
            }

            if (c == '\'') {
                inChar = true
                i++
                continue
            }

            if (!c.isWhitespace()) {
                if (firstEffectiveChar == ' ') {
                    firstEffectiveChar = c
                }
                if (c == '{') {
                    openB++
                } else if (c == '}') {
                    closeB++
                }
            }

            i++
        }

        val startsWithClose = (firstEffectiveChar == '}')
        return BraceAnalysis(openB, closeB, startsWithClose, inBlock)
    }

    fun analyzeLineBraces(line: String): Triple<Int, Int, Boolean> {
        val res = countEffectiveBraces(line, false)
        return Triple(res.openB, res.closeB, res.startsWithClose)
    }

    fun formatJavaStructure(text: String, indentSize: Int = 4): String {
        val clean = stripLeadingMargins(text)
        val lines = clean.split("\n")
        if (lines.isEmpty()) return ""

        val formattedLines = ArrayList<String>(lines.size)
        var level = 0
        val indentStr = " ".repeat(indentSize)
        var inMultilineComment = false

        for (rawLine in lines) {
            val line = rawLine.trim()

            if (line.isEmpty()) {
                formattedLines.add("")
                continue
            }

            if (inMultilineComment) {
                val commentIndent = indentStr.repeat(level) + (if (line.startsWith("*")) " " else "")
                formattedLines.add(commentIndent + line)
                val res = countEffectiveBraces(line, inBlockComment = true)
                inMultilineComment = res.inBlockComment
                continue
            }

            val analysis = countEffectiveBraces(line, inBlockComment = false)
            inMultilineComment = analysis.inBlockComment

            var effectiveLevel = level
            if (analysis.startsWithClose) {
                effectiveLevel = maxOf(0, level - 1)
            } else if (line.startsWith("case ") || line.startsWith("default:")) {
                effectiveLevel = if (level > 0) maxOf(0, level - 1) else 0
            }

            formattedLines.add(indentStr.repeat(effectiveLevel) + line)
            level = maxOf(0, level + (analysis.openB - analysis.closeB))
        }

        return formattedLines.joinToString("\n")
    }

    fun prepareForIdeMode(text: String, indentSize: Int = 4): String {
        val formatted = formatJavaStructure(text, indentSize)
        val lines = formatted.split("\n")
        if (lines.size <= 1) return formatted

        val outLines = ArrayList<String>(lines.size)
        var prevTargetIndent = 0
        var prevOpenB = 0
        var prevCloseB = 0

        for (idx in lines.indices) {
            val line = lines[idx]
            if (idx == 0) {
                outLines.add(line)
                prevTargetIndent = line.length - line.trimStart(' ').length
                val analysis = countEffectiveBraces(line)
                prevOpenB = analysis.openB
                prevCloseB = analysis.closeB
                continue
            }

            val stripped = line.trimStart(' ')
            if (stripped.isEmpty()) {
                outLines.add("")
                continue
            }

            val targetIndent = line.length - stripped.length
            val analysis = countEffectiveBraces(stripped)
            val currOpenB = analysis.openB
            val currCloseB = analysis.closeB
            val startsWithClose = analysis.startsWithClose

            val editorIndent = if (prevOpenB > prevCloseB) {
                prevTargetIndent + ((prevOpenB - prevCloseB) * indentSize)
            } else {
                prevTargetIndent
            }

            val adjustedLine = if (startsWithClose) {
                val effectiveEditorIndent = maxOf(0, editorIndent - indentSize)
                val spacesNeeded = maxOf(0, targetIndent - effectiveEditorIndent)
                " ".repeat(spacesNeeded) + stripped
            } else {
                if (targetIndent > editorIndent) {
                    val spacesNeeded = targetIndent - editorIndent
                    " ".repeat(spacesNeeded) + stripped
                } else if (targetIndent < editorIndent) {
                    val backspacesNeeded = editorIndent - targetIndent
                    "\b".repeat(backspacesNeeded) + stripped
                } else {
                    stripped
                }
            }

            outLines.add(adjustedLine)
            prevTargetIndent = targetIndent
            prevOpenB = currOpenB
            prevCloseB = currCloseB
        }

        return outLines.joinToString("\n")
    }
}
