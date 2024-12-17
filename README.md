# GitHub Ops CLI

A powerful command-line tool for automating GitHub operations, including version management, release creation, and submodule updates. This tool is designed to be used both locally and in CI/CD pipelines.

## Features

- Version management (get and bump versions)
- Automated release creation
- Submodule updates with automatic PR creation
- Support for semantic versioning and timestamp-based versioning
- Integration with GitHub's API
- Docker support for containerized operations

## Prerequisites

- Python 3.9+
- Docker (for containerized usage)
- GitHub Personal Access Token with appropriate permissions
- Google Cloud SDK (for pushing to Google Container Registry)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/github-ops-cli.git
cd github-ops-cli
```

2. Install dependencies:
```bash
make install
```

## Configuration

Set your GitHub token as an environment variable:
```bash
export GITHUB_TOKEN=your_github_token
```

## Usage

### Local Usage

The CLI supports several actions:

1. Get Latest Version:
```bash
python cli.py --action get-version \
    --repo-owner <owner> \
    --repo-name <repo>
```

2. Bump Version:
```bash
python cli.py --action bump-version \
    --repo-owner <owner> \
    --repo-name <repo> \
    --current-version v1.0.0 \
    --version-type patch
```

3. Create Release:
```bash
python cli.py --action create-release \
    --repo-owner <owner> \
    --repo-name <repo> \
    --current-version v1.0.1
```

4. Update Submodule:
```bash
python cli.py --action update-submodule \
    --repo-owner <owner> \
    --repo-name <repo> \
    --parent-repo <parent> \
    --submodule-path <path> \
    --is-merge true
```

### Docker Usage

Build and run using Docker:

```bash
make build
docker run --rm \
    -e GITHUB_TOKEN=${GITHUB_TOKEN} \
    github-ops-builder \
    --action get-version \
    --repo-owner <owner> \
    --repo-name <repo>
```

### Development

1. Run local tests:
```bash
make test-local
```

2. Run all tests:
```bash
make test-all
```

3. Build and deploy Docker image:
```bash
make deploy
```

## Available Make Commands

- `make install` - Install Python dependencies locally
- `make setup` - Create necessary directories
- `make build` - Build the Docker image
- `make test` - Test the Docker image
- `make test-local` - Run CLI tests locally
- `make test-all` - Run all Docker-based tests
- `make push` - Push the image to Docker repository
- `make deploy` - Configure Docker, build, test, and push
- `make clean` - Clean up build artifacts
- `make help` - Display help message

## Version Types

The tool supports different version bump types:
- `major` - Bump major version (x.0.0)
- `minor` - Bump minor version (0.x.0)
- `patch` - Bump patch version (0.0.x)
- `timestamp` - Add timestamp to version (v1.0.0-20240116120000)

## CI/CD Integration

This tool is designed to work seamlessly in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run GitHub Ops
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          docker run --rm \
            -e GITHUB_TOKEN \
            github-ops-builder \
            --action create-release \
            --repo-owner ${{ github.repository_owner }} \
            --repo-name ${{ github.event.repository.name }} \
            --current-version v1.0.0
```

## Troubleshooting

### Common Issues

1. Authentication Errors
```
Solution: Ensure your GITHUB_TOKEN environment variable is set and has the required permissions
```

2. Docker Build Failures
```
Solution: Make sure Docker is running and you have the necessary permissions
```

3. Version File Not Found
```
Solution: Check that current_version.txt exists in your working directory for bump-version operations
```

4. Submodule Update Failures
```
Solution: Verify that the parent repository exists and you have write permissions
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Author

Abigail Ranson

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- GitHub API
- Docker
- Python Requests library