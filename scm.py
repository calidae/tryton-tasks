#!/usr/bin/env python

from invoke import task, run
import hgapi
import git
from multiprocessing import Process
from .utils import t, read_config_file
import os
import sys
import subprocess
from blessings import Terminal

MAX_PROCESSES = 20


@task()
def repo_list(config=None, gitOnly=False, unstable=True, verbose=False):
    Config = read_config_file(config, unstable=unstable)

    repos = {
        'git': [],
        'hg': []
    }
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        url = Config.get(section, 'url')
        repo_path = Config.get(section, 'path')
        repos[repo] += [(section, url, repo_path)]

    if gitOnly:
        del repos['hg']

    for key, values in repos.iteritems():
        print >> sys.stderr, "Repositories in  " + t.bold(key)
        for val in values:
            name, url, repo_path = val
            if not verbose:
                print >> sys.stderr, name
            else:
                print >> sys.stderr, name, repo_path, url


def wait_processes(processes, maximum=MAX_PROCESSES):
    i = 0
    while len(processes) > maximum:
        if i >= len(processes):
            i = 0
        p = processes[i]
        p.join(0.1)
        if p.is_alive():
            i += 1
        else:
            del processes[i]

def hg_clone(url, path, branch=None):
    command = 'hg clone -q %s %s' % (url, path)
    try:
        run(command)
    except:
        print >> sys.stderr, "Error running " + t.bold(command)
        raise
    print "Repo " + t.bold(path) + t.green(" Cloned")


def git_clone(url, path, branch="master"):
    command = 'git clone -b %s -q %s %s' % (branch, url, path)
    if not path.endswith(os.path.sep):
        path += os.path.sep
    try:
        run(command)
        # Create .hg directory so hg diff on trytond does not
        # show git repositories.
        run('mkdir %s.hg' % path)
    except:
        print >> sys.stderr, "Error running " + t.bold(command)
        raise
    print "Repo " + t.bold(path) + t.green(" Cloned")


@task()
def clone(config=None, unstable=True):
    # Updates config repo to get new repos in config files
    hg_pull('config', '.', True)

    Config = read_config_file(config, unstable=unstable)
    p = None
    processes = []
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        url = Config.get(section, 'url')
        repo_path = Config.get(section, 'path')
        branch = False
        if repo == 'hg':
            func = hg_clone
        elif repo == 'git':
            if Config.has_option(section, 'branch'):
                branch = Config.get(section, 'branch')
            func = git_clone
        else:
            print >> sys.stderr, "Not developed yet"
            continue
        path = os.path.join(repo_path, section)
        if not os.path.exists(path):
            print "Adding Module " + t.bold(section) + " to clone list"
            p = Process(target=func, args=(url, path, branch))
            p.start()
            processes.append(p)
            wait_processes(processes)
    wait_processes(processes, 0)


def hg_status(module, path, verbose, url):
    repo_path = os.path.join(path, module)
    if not os.path.exists(repo_path):
        print >> sys.stderr, t.red("Missing repositori: ") + t.bold(repo_path)
        return
    repo = hgapi.Repo(repo_path)
    actual_url = str(repo.config('paths', 'default')).rstrip('/')
    url = str(url).rstrip('/')

    msg = []
    if actual_url != url:
        msg.append(t.red("Repo URL differs: ")
            + t.bold(actual_url + " != " + url))

    st = repo.hg_status(empty=True)
    if st:
        if st.get('A'):
            for file_name in st['A']:
                msg.append(t.green('A ' + file_name))
        if st.get('M'):
            for file_name in st['M']:
                msg.append(t.yellow('M ' + file_name))
        if st.get('R'):
            for file_name in st['R']:
                msg.append(t.red('R ' + file_name))
        if st.get('!'):
            for file_name in st['!']:
                msg.append(t.bold_red('! ' + file_name))
        if st.get('?'):
            for file_name in st['?']:
                msg.append(t.blue('? ' + file_name))
    if msg:
        msg.insert(0, t.bold_red('[' + module + ']'))
    elif verbose:
        msg.append(t.bold_green('[' + module + ']'))
    if msg:
        print '\n'.join(msg) + '\n'


def git_status(module, path, verbose, url):
    repo_path = os.path.join(path, module)
    if not os.path.exists(repo_path):
        print >> sys.stderr, t.red("Missing repositori: ") + t.bold(repo_path)
        return
    repo = git.Repo(repo_path)
    config = repo.config_reader()
    config.read()
    msg = []
    actual_url = config.get_value('remote "origin"', 'url')
    if actual_url != url:
        msg.append(t.red('Repo URL differs: ') + t.bold(actual_url +
                ' != ' + url))
    diff = repo.index.diff(None)
    if diff:
        for d in diff.iter_change_type('A'):
            msg.append(t.green('A ' + d.b_blob.path))
        for d in diff.iter_change_type('M'):
            msg.append(t.yellow('M ' + d.a_blob.path))
        for d in diff.iter_change_type('R'):
            msg.append(t.blue('R %s -> %s' % (d.a_blob.path, d.b_blob.path)))
        for d in diff.iter_change_type('D'):
            msg.append(t.bold_red('D ' + d.a_blob.path))
    if msg:
        msg.insert(0, t.bold_red('[' + module + ']'))
    elif verbose:
        msg.append(t.bold_green('[' + module + ']'))
    if msg:
        print '\n'.join(msg) + '\n'


@task
def status(config=None, unstable=True, verbose=False):
    Config = read_config_file(config, unstable=unstable)
    processes = []
    p = None
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        url = Config.get(section, 'url')
        if repo == 'hg':
            func = hg_status
        elif repo == 'git':
            func = git_status
        else:
            print >> sys.stderr, "Not developed yet"
            continue
        p = Process(target=func, args=(section, path, verbose, url))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_resolve(module, path, verbose, action, tool, nostatus, include,
        exclude):
    repo_path = os.path.join(path, module)
    if not os.path.exists(repo_path):
        print >> sys.stderr, t.red("Missing repositori: ") + t.bold(repo_path)
        return

    assert action and action in ('merge', 'mark', 'unmark', 'list'), (
        "Invalid 'action' parameter for 'resolve': %s\nIt must to be 'merge', "
        "'list', 'mark', or 'unmark'." % action)

    repo = hgapi.Repo(repo_path)

    cmd = ['resolve']
    if action != 'merge':
        cmd.append('--%s' % action)
        if action == 'list':
            if nostatus:
                cmd.append('--no-status')
    else:
        if tool:
            assert tool in ('internal:dump', 'internal:fail', 'internal:local',
                'internal:merge', 'internal:other', 'internal:prompt'), (
                    "Invalid 'tool' parameter for 'resolve'. Look at "
                    "'hg help merge-tools' to know which tools are available.")
            cmd += ['-t', tool]
    if not include and not exclude:
        cmd.append('--all')
    else:
        if include:
            for pattern in include.split(','):
                cmd += ['-I', pattern]
        if exclude:
            for pattern in exclude.split(','):
                cmd += ['-X', pattern]

    try:
        out = repo.hg_command(*cmd)
    except hgapi.HgException, e:
        print t.bold_red('[' + module + ']')
        print "Error running %s (%s): %s" % (t.bold(*cmd), e.exit_code, str(e))
        return
    if out:
        print t.bold("= " + module + " =")
        print out


@task
def resolve(config=None, unstable=True, verbose=False, action='merge',
        tool=None, nostatus=False, include=None, exclude=None):
    Config = read_config_file(config, unstable=unstable)
    processes = []
    p = None
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        if repo == 'hg':
            func = hg_resolve
        else:
            print >> sys.stderr, "Not developed yet"
            continue
        p = Process(target=func, args=(section, path, verbose, action, tool,
                nostatus, include, exclude))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_diff(module, path, verbose, rev1, rev2):
    t = Terminal()
    try:
        msg = []
        path_repo = os.path.join(path, module)
        if not os.path.exists(path_repo):
            print >> sys.stderr, (t.red("Missing repositori:")
                + t.bold(path_repo))
            return

        if not verbose:
            result = run('cd %s;hg diff --stat' % path_repo, hide='stdout')
            if result.stdout:
                msg.append(t.bold(module + "\n"))
                msg.append(result.stdout)
                print "\n".join(msg)
            return
        repo = hgapi.Repo(path_repo)
        msg = []
        for diff in repo.hg_diff(rev1, rev2):
            if diff:
                d = diff['diff'].split('\n')
                for line in d:
                    if line and line[0] == '-':
                        line = t.red + line + t.normal
                    elif line and line[0] == '+':
                        line = t.green + line + t.normal

                    if line:
                        msg.append(line)
        if msg == []:
            return
        msg.insert(0, t.bold('\n[' + module + "]\n"))
        print "\n".join(msg)
    except:
        msg.insert(0, t.bold('\n[' + module + "]\n"))
        msg.append(str(sys.exc_info()[1]))
        print >> sys.stderr, "\n".join(msg)


@task
def diff(config=None, unstable=True, verbose=True, rev1='default', rev2=None):
    Config = read_config_file(config, unstable=unstable)
    processes = []
    for section in Config.sections():
        path = Config.get(section, 'path')
        p = Process(target=hg_diff, args=(section, path, verbose, rev1, rev2))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_summary(module, path, verbose):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return
    repo = hgapi.Repo(path_repo)
    cmd = ['summary', '--remote']
    summary = repo.hg_command(*cmd)
    print t.bold("= " + module + " =")
    print summary


@task
def summary(config=None, unstable=True, verbose=False):
    Config = read_config_file(config, unstable=unstable)
    processes = []
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        func = hg_summary
        if repo != 'hg':
            print >> sys.stderr, "Not developed yet"
            continue
        p = Process(target=func, args=(section, path, verbose))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_outgoing(module, path, verbose):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return
    repo = hgapi.Repo(path_repo)
    cmd = ['outgoing']
    if verbose:
        cmd.append('-v')

    try:
        out = repo.hg_command(*cmd)
    except hgapi.HgException, e:
        if 'no changes found' in str(e):
            return
        print t.bold_red('[' + module + ']')
        print "Error running %s (%s): %s" % (t.bold(*cmd), e.exit_code, str(e))
        return
    if out:
        print t.bold("= " + module + " =")
        print out


@task
def outgoing(config=None, unstable=True, verbose=False):
    Config = read_config_file(config, unstable=unstable)
    processes = []
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        func = hg_outgoing
        if repo != 'hg':
            print >> sys.stderr, "Not developed yet"
            continue
        p = Process(target=func, args=(section, path, verbose))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_pull(module, path, update):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return

    cwd = os.getcwd()
    os.chdir(path_repo)

    cmd = ['hg', 'pull']
    if update:
        cmd.append('-u')
        cmd.append('-y')  # noninteractive
    result = run(' '.join(cmd), warn=True, hide='both')

    if not result.ok:
        print >> sys.stderr, t.red("= " + module + " = KO!")
        print >> sys.stderr, result.stderr
        os.chdir(cwd)
        return

    if "no changes found" in result.stdout:
        os.chdir(cwd)
        return

    print t.bold("= " + module + " =")
    print result.stdout
    os.chdir(cwd)


def git_pull(module, path, update):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return

    cwd = os.getcwd()
    os.chdir(path_repo)

    cmd = ['git', 'pull']
    result = run(' '.join(cmd), warn=True, hide='both')

    if not result.ok:
        print >> sys.stderr, t.red("= " + module + " = KO!")
        print >> sys.stderr, result.stderr
        os.chdir(cwd)
        return

    # If mercurial outputs 'no changes found'
    # or git outputs 'Already up-to-date' do not print anything.
    if ('no changes found' in result.stdout
            or 'Already up-to-date' in result.stdout):
        os.chdir(cwd)
        return

    print t.bold("= " + module + " =")
    print result.stdout
    os.chdir(cwd)


@task
def pull(config=None, unstable=True, update=True):
    Config = read_config_file(config, unstable=unstable)
    processes = []
    p = None
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        if repo == 'hg':
            func = hg_pull
        elif repo == 'git':
            func = git_pull
        else:
            print >> sys.stderr, "Not developed yet"
            continue
        p = Process(target=func, args=(section, path, update))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_update(module, path, clean):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return

    cwd = os.getcwd()
    os.chdir(path_repo)

    cmd = ['hg', 'update']
    if clean:
        cmd.append('-C')
    else:
        cmd.append('-y')  # noninteractive
    result = run(' '.join(cmd), warn=True, hide='both')

    if not result.ok:
        print >> sys.stderr, t.red("= " + module + " = KO!")
        print >> sys.stderr, result.stderr
        os.chdir(cwd)
        return

    if (u"0 files updated, 0 files merged, 0 files removed, 0 "
            u"files unresolved\n") in result.stdout:
        os.chdir(cwd)
        return

    print t.bold("= " + module + " =")
    print result.stdout
    os.chdir(cwd)


@task
def update(config=None, unstable=True, clean=False):
    Config = read_config_file(config, unstable=unstable)
    processes = []
    p = None
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        func = hg_update
        if repo == 'git':
            continue
        if repo != 'hg':
            print >> sys.stderr, "Not developed yet"
            continue
        p = Process(target=func, args=(section, path, clean))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)

@task()
def fetch():
    print t.bold('Reverting patches...')
    bashCommand = ['quilt', 'pop', '-fa']
    output, err = execBashCommand(bashCommand)
    if not err:
        print output
    else:
        print "It's not possible to remove patche(es)"
        print err
        print t.bold('Not Fetched.')
        return
    print t.bold('Pulling and updated local repository...')
    bashCommand = ['hg', 'pull', '-u']
    output, err = execBashCommand(bashCommand)
    if not err:
        print output
    else:
        print "It's not possible to pull the local repostory. Err:"
        print err
    print t.bold('Pulling...')
    pull()
    print t.bold('Updating...')
    update()
    print t.bold('Cloning...')
    clone()
    print t.bold('Applaing patches...')
    bashCommand = ['quilt', 'push', '-a']
    output, err = execBashCommand(bashCommand)
    if not err:
        print output
    else:
        print "It's not possible to apply patche(es)"
        print err
    print t.bold('Fetched.')

def execBashCommand(bashCommand):
    """
        Execute bash command.
        @bashCommand: is list with the command and the options
        return: list with the output and the posible error
    """
    process = subprocess.Popen(bashCommand, stdout=subprocess.PIPE)
    output, err = process.communicate()
    return output, err
