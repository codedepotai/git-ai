# Git AI
Dataset and model support for the Git client.

# To test:
`python -m pip install -e path/to/root/git-ai`

# JSON Schema:

Scalar:
```
dataType: DataTypeEnum!
title: String
values: Array[Float]!
x_title: String
```

Hparam:
```
values: Array[Metric]!
```

Extra Types:
```
Metric = {
    label: String!
    unit: String
    dataType: DataTypeEnum!
    value: String!
}

DataTypeEnum = Enum {
    FLOAT
    STRING
    INT
    BOOLEAN
}
```

# Git errors:
To git@git.testdomain.com:sometest.git
! [rejected] your-branch -] your-branch (non-fast-forward)

fatal: not a git repository

fatal: repository not found

fatal: refusing to merge unrelated histories

fatal: refusing to merge unrelated histories
Error redoing merge 1234deadbeef1234deadbeef

interactive rebase in progress; onto 4321beefdead
Last command done (1 command done):
   pick 1234deadbeef1234deadbeef test merge commit

xcrun: error: invalid active developer path (/Library/Developer/CommandLineTools), missing xcrun at: /Library/Developer/CommandLineTools/usr/bin/xcrun


fatal: Unable to create '/path/to/.git/index.lock': File exists.

If no other git process is currently running, this probably means a git process crashed in this repository earlier. 

error: pathspec 'mybranch' did not match any file(s) known to git.

Initialized empty Git repository in `/path/to/test/.git/`
Permission denied (publickey).
fatal: The remote end hung up unexpectedly

