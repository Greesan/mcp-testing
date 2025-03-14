from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

mcp = FastMCP("github")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

async def make_github_request(query: str, variables: dict) -> dict[str, Any] | None:
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                GITHUB_GRAPHQL_URL,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            # Check for GraphQL-specific errors
            if "errors" in result:
                print(f"GraphQL Errors: {result['errors']}")  # Should use proper logging
                return None
                
            return result
            
        except httpx.TimeoutException:
            print("Request timed out")  # Should use proper logging
            return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code}")  # Should use proper logging
            return None
        except Exception as e:
            print(f"Unexpected error: {str(e)}")  # Should use proper logging
            return None

@mcp.tool()
async def get_repository_info(owner: str, name: str) -> str:
    """Get detailed information about a GitHub repository.
    
    Args:
        owner: Repository owner/organization
        name: Repository name
    """
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        name
        description
        url
        stargazerCount
        forkCount
        issues(states: OPEN) {
          totalCount
        }
        pullRequests(states: OPEN) {
          totalCount
        }
        primaryLanguage {
          name
        }
        languages(first: 10) {
          nodes {
            name
          }
        }
        releases(last: 1) {
          nodes {
            tagName
            publishedAt
          }
        }
      }
    }
    """
    
    variables = {"owner": owner, "name": name}
    data = await make_github_request(
        query.replace("\n", " ").strip(),
        variables
    )
    
    if not data or "data" not in data:
        return "Unable to fetch repository information."
        
    repo = data["data"]["repository"]
    if not repo:
        return f"Repository {owner}/{name} not found."
        
    languages = [lang["name"] for lang in repo["languages"]["nodes"]]
    latest_release = (repo["releases"]["nodes"][0] 
                     if repo["releases"]["nodes"] and len(repo["releases"]["nodes"]) > 0 
                     else None)
    
    return f"""
Repository: {repo['name']}
Description: {repo.get('description', 'No description')}
URL: {repo['url']}
Stars: {repo['stargazerCount']}
Forks: {repo['forkCount']}
Open Issues: {repo['issues']['totalCount']}
Open Pull Requests: {repo['pullRequests']['totalCount']}
Primary Language: {repo['primaryLanguage']['name'] if repo['primaryLanguage'] else 'None'}
Languages: {', '.join(languages)}
Latest Release: {latest_release['tagName'] + ' (' + latest_release['publishedAt'] + ')' if latest_release else 'None'}
"""

@mcp.tool()
async def get_user_info(username: str) -> str:
    """Get detailed information about a GitHub user.
    
    Args:
        username: GitHub username
    """
    query = """
    query($username: String!) {
      user(login: $username) {
        name
        login
        bio
        company
        location
        email
        websiteUrl
        repositories {
          totalCount
        }
        followers {
          totalCount
        }
        following {
          totalCount
        }
        contributionsCollection {
          totalCommitContributions
        }
      }
    }
    """
    
    variables = {"username": username}
    data = await make_github_request(
        query.replace("\n", " ").strip(),
        variables,
        GITHUB_TOKEN
    )
    
    if not data or "data" not in data:
        return "Unable to fetch user information."
        
    user = data["data"]["user"]
    if not user:
        return f"User {username} not found."
        
    return f"""
Name: {user.get('name', 'Not provided')}
Username: {user['login']}
Bio: {user.get('bio', 'No bio')}
Company: {user.get('company', 'Not provided')}
Location: {user.get('location', 'Not provided')}
Email: {user.get('email', 'Not provided')}
Website: {user.get('websiteUrl', 'Not provided')}
Public Repositories: {user['repositories']['totalCount']}
Followers: {user['followers']['totalCount']}
Following: {user['following']['totalCount']}
Total Contributions: {user['contributionsCollection']['totalCommitContributions']}
"""

if __name__ == "__main__":
    try:
        print("GitHub Stats MCP server starting...")
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        print("\nShutting down GitHub Stats MCP server...")
    except Exception as e:
        print(f"Error running GitHub Stats MCP server: {str(e)}")
        raise
