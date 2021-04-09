"""
A lookup function designed to return data from the Nautobot GraphQL endpoint
"""

from __future__ import absolute_import, division, print_function

import os

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleLookupError
import pynautobot

from ..module_utils.utils import NautobotApiBase, NautobotGraphQL

__metaclass__ = type

DOCUMENTATION = """
    lookup: lookup
    author: Josh VanDeraa (@jvanderaa)
    version_added: "1.1.0"
    short_description: Queries and returns elements from Nautobot GraphQL endpoint
    description:
        - Queries Nautobot via its GraphQL API through pynautobot
    options:
        query:
            description:
                - The GraphQL formatted query string, see [pynautobot GraphQL documentation](https://pynautobot.readthedocs.io/en/latest/advanced/graphql.html) for more details.
            required: True
        token:
            description:
                - The API token created through Nautobot
            env:
                # in order of precedence
                - name: NAUTOBOT_TOKEN
            required: False
        url:
            description:
                - The URL to the Nautobot instance to query (http://nautobot.example.com:8000)
            env:
                # in order of precedence
                - name: NAUTOBOT_URL
            required: True
        validate_certs:
            description:
                - Whether or not to validate SSL of the Nautobot instance
            required: False
            default: True
        variables:
            description:
                - Dictionary of keys/values to pass into the GraphQL query, see [pynautobot GraphQL documentation](https://pynautobot.readthedocs.io/en/latest/advanced/graphql.html) for more details
            required: False
    requirements:
        - pynautobot
"""

EXAMPLES = """
  # Make API Query without variables
  - name: SET FACT OF STRING
    set_fact:
      query_string: |
        query {
          sites {
            id
            name
            region {
              name
            }
          }
        }

  # Make query to GraphQL Endpoint
  - name: Obtain list of sites from Nautobot
    set_fact:
      query_response: "{{ query('networktocode.nautobot.lookup_graphql', query=query, url='https://nautobot.example.com', token='<redact>') }}"

  # Example with variables
  - name: SET FACTS TO SEND TO GRAPHQL ENDPOINT
    set_fact:
      variables:
        site_name: den
      query_string: |
        query ($site_name:String!) {
            sites (name: $site_name) {
            id
            name
            region {
                name
            }
            }
        }

  # Get Response with variables
  - name: Obtain list of devices from Nautobot
    set_fact:
      query_response: "{{ query('networktocode.nautobot.lookup_graphql', query=query, variables=variables url='https://nautobot.example.com', token='<redact>') }}"
"""

RETURN = """
  data:
    description:
      - Data result from the GraphQL endpoint
    type: dict
"""


def nautobot_lookup_graphql(**kwargs):
    """Lookup functionality, broken out to assist with testing

    Returns:
        [type]: [description]
    """
    # Setup API Token information, URL, and SSL verification
    url = kwargs.get("url") or os.getenv("NAUTOBOT_URL")

    # Verify URL is passed in, that it is not None
    if url is None:
        raise AnsibleLookupError("Missing URL of Nautobot")

    token = kwargs.get("token") or os.getenv("NAUTOBOT_TOKEN")
    ssl_verify = kwargs.get("validate_certs", True)

    if not isinstance(ssl_verify, bool):
        raise AnsibleLookupError("validate_certs must be a boolean")

    nautobot_api = NautobotApiBase(token=token, url=url, ssl_verify=ssl_verify)
    query = kwargs.get("query")
    variables = kwargs.get("variables")

    # Check that a valid query was passed in
    if query is None:
        raise AnsibleLookupError(
            "Query parameter was not passed. Please verify that query is passed."
        )

    # Verify that the query is a string type
    if not isinstance(query, str):
        raise AnsibleLookupError(
            "Query parameter must be of type string. Please see docs for examples."
        )

    # Verify that the variables key coming in is a dictionary
    if variables is not None and not isinstance(variables, dict):
        raise AnsibleLookupError(
            "Variables parameter must be of key/value pairs. Please see docs for examples."
        )

    # Setup return results
    results = {}
    # Make call to Nautobot API and capture any failures
    nautobot_graph_obj = NautobotGraphQL(
        query_str=query, api=nautobot_api, variables=variables
    )

    # Get the response from the object
    nautobot_response = nautobot_graph_obj.query()

    # Check for errors in the response
    if isinstance(nautobot_response, pynautobot.GraphQLException):
        raise AnsibleLookupError(
            "Error in the query to the Nautobot host. Errors: %s"
            % (nautobot_response.errors)
        )

    # Good result, return it
    if isinstance(nautobot_response, pynautobot.GraphQLRecord):
        # Assign the data of a good result to the response
        results["data"] = nautobot_response.json.get("data")

    return results


class LookupModule(LookupBase):
    """
    LookupModule(LookupBase) is defined by Ansible
    """

    def run(self, **kwargs):
        """Runs Ansible Lookup Plugin for using Nautobot GraphQL endpoint

        Raises:
            AnsibleLookupError: Error in data loaded into the plugin

        Returns:
            dict: Data returned from GraphQL endpoint
        """
        lookup_info = nautobot_lookup_graphql(**kwargs)

        # Results should be the data response of the query to be returned as a lookup
        return lookup_info
