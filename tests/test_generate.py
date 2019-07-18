# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

import hglib
import pygit2
import pytest

from microannotate import generator


@pytest.fixture
def fake_hg_repo(tmpdir):
    tmp_path = tmpdir.strpath
    dest = os.path.join(tmp_path, "repos")
    local = os.path.join(dest, "local")
    os.makedirs(local)
    hglib.init(local)

    os.environ["USER"] = "app"
    hg = hglib.open(local)

    hg.branch(b"central")

    yield hg, local

    hg.close()


def add_file(hg, repo_dir, name, contents):
    path = os.path.join(repo_dir, name)

    with open(path, "w") as f:
        f.write(contents)

    hg.add(files=[bytes(path, "ascii")])


def commit(hg):
    commit_message = "Commit {}".format(
        " ".join([elem.decode("ascii") for status in hg.status() for elem in status])
    )

    i, revision = hg.commit(message=commit_message, user="Moz Illa <milla@mozilla.org>")

    return str(revision, "ascii")


def test_generate_tokenized(fake_hg_repo, tmpdir):
    hg, local = fake_hg_repo

    git_repo = os.path.join(tmpdir.strpath, "repo")

    add_file(
        hg,
        local,
        "file.cpp",
        """#include <iostream>

/* main */
int main() {
    return 0;
}""",
    )
    revision1 = commit(hg)

    add_file(
        hg,
        local,
        "file.cpp",
        """#include <iostream>

/* main */
int main() {
    cout << "Hello, world!";
    return 0;
}""",
    )
    add_file(
        hg,
        local,
        "file.jsm",
        """function ciao(str) {
  // Comment one
  console.log(str);
}""",
    )
    revision2 = commit(hg)

    generator.generate(
        local,
        git_repo,
        rev_start=0,
        rev_end="tip",
        limit=None,
        tokenize=True,
        remove_comments=False,
    )

    repo = pygit2.Repository(git_repo)
    commits = list(
        repo.walk(
            repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_REVERSE
        )
    )

    assert (
        commits[0].message
        == f"""Commit A file.cpp

UltraBlame original commit: {revision1}"""
    )

    assert (
        commits[1].message
        == f"""Commit M file.cpp A file.jsm

UltraBlame original commit: {revision2}"""
    )

    with open(os.path.join(git_repo, "file.cpp"), "r") as f:
        cpp_file = f.read()
        assert (
            cpp_file
            == """#
include
iostream
/
*
main
*
/
int
main
(
)
{
cout
"
Hello
world
"
return
0
}
"""
        )

    with open(os.path.join(git_repo, "file.jsm"), "r") as f:
        js_file = f.read()
        assert (
            js_file
            == """function
ciao
(
str
)
{
/
/
Comment
one
console
log
(
str
)
}
"""
        )


def test_generate_comments_removed(fake_hg_repo, tmpdir):
    hg, local = fake_hg_repo

    git_repo = os.path.join(tmpdir.strpath, "repo")

    add_file(
        hg,
        local,
        "file.cpp",
        """#include <iostream>

/* main */
int main() {
    return 0;
}""",
    )
    revision1 = commit(hg)

    add_file(
        hg,
        local,
        "file.cpp",
        """#include <iostream>

/* main */
int main() {
    cout << "Hello, world!";
    return 0;
}""",
    )
    add_file(
        hg,
        local,
        "file.jsm",
        """function ciao(str) {
// Comment one
  console.log(str);
}""",
    )
    revision2 = commit(hg)

    generator.generate(
        local,
        git_repo,
        rev_start=0,
        rev_end="tip",
        limit=None,
        tokenize=False,
        remove_comments=True,
    )

    repo = pygit2.Repository(git_repo)
    commits = list(
        repo.walk(
            repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_REVERSE
        )
    )

    assert (
        commits[0].message
        == f"""Commit A file.cpp

UltraBlame original commit: {revision1}"""
    )

    assert (
        commits[1].message
        == f"""Commit M file.cpp A file.jsm

UltraBlame original commit: {revision2}"""
    )

    with open(os.path.join(git_repo, "file.cpp"), "r") as f:
        cpp_file = f.read()
        assert (
            cpp_file
            == """#include <iostream>


int main() {
    cout << "Hello, world!";
    return 0;
}"""
        )

    with open(os.path.join(git_repo, "file.jsm"), "r") as f:
        js_file = f.read()
        assert (
            js_file
            == """function ciao(str) {

  console.log(str);
}"""
        )


def test_generate_tokenized_and_comments_removed(fake_hg_repo, tmpdir):
    hg, local = fake_hg_repo

    git_repo = os.path.join(tmpdir.strpath, "repo")

    add_file(
        hg,
        local,
        "file.cpp",
        """#include <iostream>

/* main */
int main() {
    return 0;
}""",
    )
    revision1 = commit(hg)

    add_file(
        hg,
        local,
        "file.cpp",
        """#include <iostream>

/* main */
int main() {
    cout << "Hello, world!";
    return 0;
}""",
    )
    add_file(
        hg,
        local,
        "file.jsm",
        """function ciao(str) {
// Comment one
  console.log(str);
}""",
    )
    revision2 = commit(hg)

    generator.generate(
        local,
        git_repo,
        rev_start=0,
        rev_end="tip",
        limit=None,
        tokenize=True,
        remove_comments=True,
    )

    repo = pygit2.Repository(git_repo)
    commits = list(
        repo.walk(
            repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_REVERSE
        )
    )

    assert (
        commits[0].message
        == f"""Commit A file.cpp

UltraBlame original commit: {revision1}"""
    )

    assert (
        commits[1].message
        == f"""Commit M file.cpp A file.jsm

UltraBlame original commit: {revision2}"""
    )

    with open(os.path.join(git_repo, "file.cpp"), "r") as f:
        cpp_file = f.read()
        assert (
            cpp_file
            == """#
include
iostream
int
main
(
)
{
cout
"
Hello
world
"
return
0
}
"""
        )

    with open(os.path.join(git_repo, "file.jsm"), "r") as f:
        js_file = f.read()
        assert (
            js_file
            == """function
ciao
(
str
)
{
console
log
(
str
)
}
"""
        )


def test_generate_comments_removed_no_comments(fake_hg_repo, tmpdir):
    hg, local = fake_hg_repo

    git_repo = os.path.join(tmpdir.strpath, "repo")

    add_file(
        hg,
        local,
        "file.cpp",
        """#include <iostream>

int main() {
    return 0;
}""",
    )
    revision1 = commit(hg)

    generator.generate(
        local,
        git_repo,
        rev_start=0,
        rev_end="tip",
        limit=None,
        tokenize=False,
        remove_comments=True,
    )

    repo = pygit2.Repository(git_repo)
    commits = list(
        repo.walk(
            repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_REVERSE
        )
    )

    assert (
        commits[0].message
        == f"""Commit A file.cpp

UltraBlame original commit: {revision1}"""
    )

    with open(os.path.join(git_repo, "file.cpp"), "r") as f:
        cpp_file = f.read()
        assert (
            cpp_file
            == """#include <iostream>

int main() {
    return 0;
}"""
        )


def test_generate_comments_removed_unusupporte_extension(fake_hg_repo, tmpdir):
    hg, local = fake_hg_repo

    git_repo = os.path.join(tmpdir.strpath, "repo")

    add_file(
        hg,
        local,
        "file.surely_unsupported",
        """#include <iostream>

/* main */
int main() {
    return 0;
}""",
    )
    revision1 = commit(hg)

    generator.generate(
        local,
        git_repo,
        rev_start=0,
        rev_end="tip",
        limit=None,
        tokenize=False,
        remove_comments=True,
    )

    repo = pygit2.Repository(git_repo)
    commits = list(
        repo.walk(
            repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_REVERSE
        )
    )

    assert (
        commits[0].message
        == f"""Commit A file.surely_unsupported

UltraBlame original commit: {revision1}"""
    )

    with open(os.path.join(git_repo, "file.surely_unsupported"), "r") as f:
        cpp_file = f.read()
        assert (
            cpp_file
            == """#include <iostream>

/* main */
int main() {
    return 0;
}"""
        )