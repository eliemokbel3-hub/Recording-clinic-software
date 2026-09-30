# Your own template defaults (one clinic)

When the scribe writes a draft into a Cliniko treatment note, it checks every
question its template setup can fill — not only the ones this note has text
for. Each of those must still hold only the text the new note **started
with**; text you typed yourself into any of them stops the write. Questions
the scribe never fills are kept as they are. By default the scribe reads that starting text from
the note's Cliniko template ("Cliniko template" on the **Clinics** tab). If a
clinic's notes start with text the template does not hold, switch that clinic
to **My own defaults** and describe the starting text in a file.

## Where the file goes

One file per clinic, named after the clinic's web address:

```
%LOCALAPPDATA%\ClinikoScribe\config\template_defaults\<clinic web address>.json
```

For example `...\template_defaults\northside.au2.cliniko.com.json`. The
Clinics tab shows the exact path once the clinic uses "My own defaults". The
scribe never creates or changes this file or its folder — you do. Removing a
clinic from the app leaves the file in place.

## What it holds

```json
{
  "schema_version": 1,
  "templates": {
    "Standard Consultation": {
      "History": {
        "Presenting complaint": ["Site -", "Chron -", "Agg -"]
      }
    }
  }
}
```

- **Template, section and question names** are written exactly as Cliniko
  shows them, each as its own key (never joined with a slash — some Cliniko
  names already contain one). Each name is one line of at most 100
  characters.
- **The starting text** of a question is a string, or a list of lines (as
  above; the lines are joined with line breaks). Write it as Cliniko's editor
  shows it — plain visible text, not HTML. It may not be empty or blank
  (leave the question out instead) and may be at most 4 000 characters. A
  line break is the only control character allowed.
- **A question you leave out** starts empty, so list the starting text of
  every question the scribe fills that has any — otherwise that text counts
  as typed and the write is refused. `{}` under a template name means "this
  template starts with no text".
- **Every template you write with needs an entry.** A write for a template
  the file does not name is refused, and so is a file that names a section or
  question the note's template does not have.
- Save the file as UTF-8 (Notepad: "Save as", Encoding "UTF-8"). The whole
  file is at most 64 KB. A template name may appear only once, and a section
  or question name only once inside the same template or section.
- Starting text only — never put patient details in this file. It is plain
  text on this computer.
- **The file decides what a write may replace.** Text in a note that matches
  an entry here counts as untyped, so the write replaces it. If an entry
  matched something you would type yourself, a write could replace your
  typing — keep each entry to the note's real starting text.
- A question whose starting text in Cliniko holds a picture or a horizontal
  line cannot be told apart from typed content, so a write to such a note is
  refused ("The Cliniko note already holds text …"); copy the note instead.

## Checking it

On the **Clinics** tab, select the clinic and press **Check file**. It reads
the file (no Cliniko request) and says whether it can be used, or names the
first problem and where it is. The names are matched against the note's own
Cliniko template only when you press **Write draft to Cliniko**, so a file
that passes Check file can still be refused then — the Note tab says why.
