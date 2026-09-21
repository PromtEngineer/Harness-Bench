# flowkit CLI contract

The CLI lives at flowkit/cli.py and is invoked as `python3 -m flowkit.cli`.

## Subcommands

### run <pipeline.json> --input <text>
Build a Pipeline from the JSON file and run it on the input text; print
the result to stdout followed by a newline. Exit 0.

### list
Print the names of all registered steps, sorted, one per line. Exit 0.

### describe <pipeline.json>
Build the Pipeline and print Pipeline.to_json() followed by a newline.
Exit 0.

## Pipeline file format

A JSON array of {"step": <registered name>, "cfg": {<constructor kwargs>}}
objects; "cfg" is optional.

## Errors (exact contract)

- Unknown step name NAME anywhere in the file:
  print `error: unknown step 'NAME'` to stderr, exit 2.
- File missing or not valid JSON, or not an array:
  print `error: invalid pipeline file` to stderr, exit 2.
- Unknown subcommand or missing arguments: usage text to stderr, exit 2.

No other output on stderr in success cases.
