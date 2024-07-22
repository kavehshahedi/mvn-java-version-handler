import git
import os

from mvn_service import MvnService
from pom_service import PomService

REPO = {
    'path': 'PROJECT_PATH', # The path to the Git repository
    'branch': 'BRANCH_NAME' # The branch name
}

if __name__ == '__main__':
    # Create a git repo object
    repo = git.Repo(REPO['path'])

    # Iterate over all commits in the repo
    for commit in repo.iter_commits(REPO['branch']):
        # Checkout the commit
        repo.git.checkout(commit, force=True)

        # Get the Java version from the POM file
        pom_service = PomService(os.path.join(REPO['path'], 'pom.xml'))
        java_version = pom_service.get_java_version()

        print(f'Commit: {commit.hexsha} - Java Version: {java_version}')

        # Update the Java version is less than 8 (i.e., 1.8)
        if java_version is not None and float(java_version) < 1.8:
            print(f'\tUpdating to 1.8')
            pom_service.set_java_version('1.8')

        # Install the Maven project
        mvn_service = MvnService()
        is_installed = mvn_service.install(cwd=REPO['path'], # The path to the Maven project
                            java_version=java_version, # The Java version
                            verbose=False, # Print the mvn command output or not
                            is_shell=False) # Execute the mvn command in a shell or not (normally, in Linux and macOS, it should be False)
        
        print(f'Commit: {commit.hexsha} - Installation: {is_installed}')

        # Package the Maven project
        is_packaged = mvn_service.package(cwd=REPO['path'], # The path to the Maven project
                            java_version=java_version, # The Java version
                            verbose=False, # Print the mvn command output or not
                            is_shell=False)
        
        print(f'Commit: {commit.hexsha} - Packaging: {is_packaged}')

        if is_packaged:
            # Get the Jar name
            jar_name = pom_service.get_jar_name()
            print(f'Commit: {commit.hexsha} - Jar Path: {os.path.join(REPO["path"], "target", jar_name)}')

        # Just for the sake of simplicity, we break the loop after the first commit
        exit(0)