import re
from urllib.parse import urlparse
import pygit2
import os
import paramiko
from prompt_toolkit import prompt
import subprocess

from git_ai.errors.errors import DepotError, RemoteError


class Credentials():
    def __init__(self, repo: pygit2.Repository):
        self.repo = repo
        self.working_creds = {}

    def __key_needs_password(self, filename: str):
        needs_password = False
        try:
            paramiko.RSAKey.from_private_key_file(filename)
        except paramiko.PasswordRequiredException:
            needs_password = True

        return needs_password

    def __get_ssh_keypairs(self):
        ssh_dir = os.path.join(os.path.expanduser("~"), '.ssh')
        for f in os.listdir(ssh_dir):
            if f.endswith('.pub'):
                public_key = os.path.join(ssh_dir, f)
                private_key = os.path.join(ssh_dir, f[:-4])
                if os.path.isfile(private_key) and os.path.isfile(public_key):
                    yield public_key, private_key, self.__key_needs_password(private_key)

    def try_auth(self, remote, creds, operation_fn):
        succeeded = True
        try:
            result = operation_fn(pygit2.RemoteCallbacks(credentials=creds))
        except Exception as e:
            print("Failed auth: ", e)
            succeeded = False

        if succeeded:
            self.working_creds[remote] = creds
            return succeeded, result
        else:
            return succeeded, None

    def auth_operation(self, remote, operation_fn: callable):

        if remote in self.working_creds:
            try:
                result = operation_fn(pygit2.RemoteCallbacks(
                    credentials=self.working_creds[remote]))
            except Exception as e:
                self.working_creds[remote] = None
                print(f"Failed previously working auth for {remote}: ", e)
                raise RemoteError.failed_to_auth()
            return result

        protocol = self.__get_protocol_from_url(remote)
        if protocol == "ssh":
            # TODO Check ssh config file if key is specified
            username = self.__get_ssh_user(remote)
            if 'DEPOT_SSH_PRIVATE_KEY' in os.environ:
                print("Using ai's ssh key")
                public_key = os.environ['DEPOT_SSH_PUBLIC_KEY']
                private_key = os.environ['DEPOT_SSH_PRIVATE_KEY']

                keypair = pygit2.KeypairFromMemory(
                    username, public_key, private_key, '')
                succeeded, result = self.try_auth(
                    remote, keypair, operation_fn)
                if not succeeded:
                    raise DepotError.cant_authenticate_with_depot_key()
                else:
                    return result

            print(
                f"Trying to authenticate with {remote}, using username:{username}")
            print("Trying agent authentication")
            agent_credentials = pygit2.KeypairFromAgent(username)
            succeeded, result = self.try_auth(
                remote, agent_credentials, operation_fn)
            if succeeded:
                return result

            # Try keys that don't need a password first
            print("Trying ssh key authentication without password")
            for pubkey, privkey, needs_password in self.__get_ssh_keypairs():
                if needs_password:
                    continue

                keypair = pygit2.Keypair(username, pubkey, privkey, '')
                succeeded, result = self.try_auth(
                    remote, keypair, operation_fn)
                if succeeded:
                    return result

            print("Trying ssh key authentication with password")
            for pubkey, privkey, needs_password in self.__get_ssh_keypairs():
                if not needs_password:
                    continue
                password = prompt(
                    f"Enter password for {privkey}: ", is_password=True)
                keypair = pygit2.Keypair(username, pubkey, privkey, password)
                succeeded, result = self.try_auth(
                    remote, keypair, operation_fn)
                if succeeded:
                    return result

            raise RemoteError.failed_to_auth()

        elif protocol == "http":
            credentials = self.__get_git_credentials(remote)
            if credentials:
                _, _, username, password = credentials
                userpass = pygit2.UserPass(username, password)
                succeeded, result = self.try_auth(
                    remote, userpass, operation_fn)
                if succeeded:
                    return result
            else:
                username = prompt(f"Enter your username for {remote}: ")
                password = prompt(
                    f"Enter password for {remote}: ", is_password=True)
                userpass = pygit2.UserPass(username, password)
                succeeded, result = self.try_auth(
                    remote, userpass, operation_fn)
                if succeeded:
                    return result
        elif protocol == "file" or protocol == "git":
            try:
                result = operation_fn(pygit2.RemoteCallbacks())
                return result
            except Exception as e:
                del self.working_creds[remote]
                raise RemoteError.failed_to_auth()
        else:
            raise RemoteError.unrecognized_protocol(remote)

    def __get_git_credentials(self, remote: str):
        helper_cmd = ['git', 'credential', 'fill']
        input_cred = f'url={remote}'
        try:
            # Call the Git credential helper
            process = subprocess.Popen(
                helper_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(input=input_cred.encode())
            if process.returncode == 0:
                output = stdout.decode()
                # Parse output for username and password if needed
                return self.__parse_git_credentials_output(output)
            else:
                return None
        except Exception as e:
            raise RemoteError.credential_helper()

    def __parse_git_credentials_output(self, output: str):
        # Split the output into lines and remove any whitespace or empty lines
        lines = [line.strip()
                 for line in output.strip().split("\n") if line.strip()]

        # Initialize a dictionary to hold the credentials
        credentials = {}

        # Loop through each line, split by '=', and populate the dictionary
        try:
            for line in lines:
                key, value = line.split("=", 1)  # Split on the first '=' found
                credentials[key] = value

            # Extract the specific values
            protocol = credentials.get("protocol")
            host = credentials.get("host")
            username = credentials.get("username")
            password = credentials.get("password")
            return protocol, host, username, password
        except Exception:
            return None

    def __get_protocol_from_url(self, url: str):
        parse_result = urlparse(url)
        if parse_result.scheme:
            scheme = parse_result.scheme
            if scheme == "http" or scheme == "https":
                return "http"
            elif scheme == "ssh" or scheme == "rsync":
                return "ssh"
            else:
                return scheme
        else:
            if re.match(r"^[a-zA-Z0-9-_]+@", url):
                return "ssh"
            else:
                return "file"

    def __get_ssh_user(self, url: str):
        parse_result = urlparse(url)
        if parse_result.username:
            return parse_result.username
        else:
            if re.match(r"^[a-zA-Z0-9-_]+@", url):
                return url.split("@")[0]
            else:
                return "git"
