"""
github3.pulls
=============

This module contains all the classes relating to pull requests.

"""

from re import match
from json import dumps
from github3.git import Commit
from github3.models import GitHubObject, GitHubCore, BaseComment
from github3.users import User
from github3.decorators import requires_auth


class PullDestination(GitHubCore):
    """The :class:`PullDestination <PullDestination>` object."""
    def __init__(self, dest, direction):
        super(PullDestination, self).__init__(None)
        #: Direction of the merge with respect to this destination
        self.direction = direction
        #: Full reference string of the object
        self.ref = dest.get('ref')
        #: label of the destination
        self.label = dest.get('label')
        #: :class:`User <github3.users.User>` representing the owner
        self.user = None
        if dest.get('user'):
            self.user = User(dest.get('user'), None)
        #: SHA of the commit at the head
        self.sha = dest.get('sha')
        self._repo_name = ''
        self._repo_owner = ''
        if dest.get('repo'):
            self._repo_name = dest['repo'].get('name')
            self._repo_owner = dest['repo']['owner'].get('login')
        self.repo = (self._repo_owner, self._repo_name)

    def __repr__(self):
        return '<{0} [{1}]>'.format(self.direction, self.label)


class PullFile(GitHubObject):
    """The :class:`PullFile <PullFile>` object."""
    def __init__(self, pfile):
        super(PullFile, self).__init__(pfile)
        #: SHA of the commit
        self.sha = pfile.get('sha')
        #: Name of the file
        self.filename = pfile.get('filename')
        #: Status of the file, e.g., 'added'
        self.status = pfile.get('status')
        #: Number of additions on this file
        self.additions = pfile.get('additions')
        #: Number of deletions on this file
        self.deletions = pfile.get('deletions')
        #: Number of changes made to this file
        self.changes = pfile.get('changes')
        #: URL to view the blob for this file
        self.blob_url = pfile.get('blob_url')
        #: URL to view the raw diff of this file
        self.raw_url = pfile.get('raw_url')
        #: Patch generated by this pull request
        self.patch = pfile.get('patch')

    def __repr__(self):
        return '<Pull Request File [{0}]>'.format(self.filename)


class PullRequest(GitHubCore):
    """The :class:`PullRequest <PullRequest>` object."""
    def __init__(self, pull, session=None):
        super(PullRequest, self).__init__(pull, session)
        self._api = pull.get('url', '')
        #: Base of the merge
        self.base = PullDestination(pull.get('base'), 'Base')
        #: Body of the pull request message
        self.body = pull.get('body', '')
        #: Body of the pull request as HTML
        self.body_html = pull.get('body_html', '')
        #: Body of the pull request as plain text
        self.body_text = pull.get('body_text', '')

        # If the pull request has been closed
        #: datetime object representing when the pull was closed
        self.closed_at = pull.get('closed_at')
        if self.closed_at:
            self.closed_at = self._strptime(self.closed_at)

        #: datetime object representing when the pull was created
        self.created_at = self._strptime(pull.get('created_at'))
        #: URL to view the diff associated with the pull
        self.diff_url = pull.get('diff_url')
        #: The new head after the pull request
        self.head = PullDestination(pull.get('head'), 'Head')
        #: The URL of the pull request
        self.html_url = pull.get('html_url')
        #: The unique id of the pull request
        self.id = pull.get('id')
        #: The URL of the associated issue
        self.issue_url = pull.get('issue_url')

        # These are the links provided by the dictionary in the json called
        # '_links'. It's structure is horrific, so to make this look a lot
        # cleaner, I reconstructed what the links would be:
        #  - ``self`` is just the api url, e.g.,
        #    https://api.github.com/repos/:user/:repo/pulls/:number
        #  - ``comments`` is just the api url for comments on the issue, e.g.,
        #    https://api.github.com/repos/:user/:repo/issues/:number/comments
        #  - ``issue`` is the api url for the issue, e.g.,
        #    https://api.github.com/repos/:user/:repo/issues/:number
        #  - ``html`` is just the html_url attribute
        #  - ``review_comments`` is just the api url for the pull, e.g.,
        #    https://api.github.com/repos/:user/:repo/pulls/:number/comments
        #: Dictionary of _links
        self.links = {
            'self': self._api,
            'comments': '/'.join([self._api.replace('pulls', 'issues'),
                                  'comments']),
            'issue': self._api.replace('pulls', 'issues'),
            'html': self.html_url,
            'review_comments': self._api + '/comments'
        }

        #: SHA of the merge commit
        self.merge_commit_sha = pull.get('merge_commit_sha', '')
        #: datetime object representing when the pull was merged
        self.merged_at = pull.get('merged_at')
        # If the pull request has been merged
        if self.merged_at:
            self.merged_at = self._strptime(self.merged_at)
        #: Whether the pull is deemed mergeable by GitHub
        self.mergeable = pull.get('mergeable', False)
        #: Whether it would be a clelan merge or not
        self.mergeable_state = pull.get('mergeable_state', '')
        #: SHA of the merge commit
        self.merge_commit_sha = pull.get('merge_commit_sha', '')
        #: :class:`User <github3.users.User>` who merged this pull
        self.merged_by = pull.get('merged_by')
        if self.merged_by:
            self.merged_by = User(self.merged_by, self)
        #: Number of the pull/issue on the repository
        self.number = pull.get('number')
        #: The URL of the patch
        self.patch_url = pull.get('patch_url')

        m = match('https://github\.com/(\S+)/(\S+)/issues/\d+',
                  self.issue_url)
        #: Returns ('owner', 'repository') this issue was filed on.
        self.repository = m.groups()
        #: The state of the pull
        self.state = pull.get('state')
        #: The title of the request
        self.title = pull.get('title')
        #: datetime object representing the last time the object was changed
        self.updated_at = self._strptime(pull.get('updated_at'))
        #: :class:`User <github3.users.User>` object representing the creator
        #  of the pull request
        self.user = pull.get('user')
        if self.user:
            self.user = User(self.user, self)

    def __repr__(self):
        return '<Pull Request [#{0}]>'.format(self.number)

    def _update_(self, pull):
        self.__init__(pull, self._session)

    @requires_auth
    def close(self):
        """Closes this Pull Request without merging.

        :returns: bool
        """
        return self.update(self.title, self.body, 'closed')

    def diff(self):
        """Return the diff"""
        resp = self._get(self._api,
                         headers={'Accept': 'application/vnd.github.diff'})
        return resp.content if self._boolean(resp, 200, 404) else None

    def is_merged(self):
        """Checks to see if the pull request was merged.

        :returns: bool
        """
        url = self._build_url('merge', base_url=self._api)
        return self._boolean(self._get(url), 204, 404)

    def iter_comments(self, number=-1, etag=None):
        """Iterate over the comments on this pull request.

        :param int number: (optional), number of comments to return. Default:
            -1 returns all available comments.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`ReviewComment <ReviewComment>`\ s
        """
        url = self._build_url('comments', base_url=self._api)
        return self._iter(int(number), url, ReviewComment, etag=etag)

    def iter_commits(self, number=-1, etag=None):
        """Iterates over the commits on this pull request.

        :param int number: (optional), number of commits to return. Default:
            -1 returns all available commits.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`Commit <github3.git.Commit>`\ s
        """
        url = self._build_url('commits', base_url=self._api)
        return self._iter(int(number), url, Commit, etag=etag)

    def iter_files(self, number=-1, etag=None):
        """Iterate over the files associated with this pull request.

        :param int number: (optional), number of files to return. Default:
            -1 returns all available files.
        :param str etag: (optional), ETag from a previous request to the same
            endpoint
        :returns: generator of :class:`PullFile <PullFile>`\ s
        """
        url = self._build_url('files', base_url=self._api)
        return self._iter(int(number), url, PullFile, etag=etag)

    @requires_auth
    def merge(self, commit_message=''):
        """Merge this pull request.

        :param str commit_message: (optional), message to be used for the
            merge commit
        :returns: bool
        """
        data = None
        if commit_message:
            data = {'commit_message': commit_message}
        url = self._build_url('merge', base_url=self._api)
        resp = self._put(url, data=dumps(data))
        self.merge_commit_sha = resp['merge_commit_sha']
        return resp.json['merged']

    def patch(self):
        """Return the patch"""
        resp = self._get(self._api,
                         headers={'Accept': 'application/vnd.github.patch'})
        return resp.content if self._boolean(resp, 200, 404) else None

    @requires_auth
    def reopen(self):
        """Re-open a closed Pull Request.

        :returns: bool
        """
        return self.update(self.title, self.body, 'open')

    @requires_auth
    def update(self, title=None, body=None, state=None):
        """Update this pull request.

        :param str title: (optional), title of the pull
        :param str body: (optional), body of the pull request
        :param str state: (optional), ('open', 'closed')
        :returns: bool
        """
        data = {'title': title, 'body': body, 'state': state}
        json = None
        for (k, v) in list(data.items()):
            if v is None:
                del data[k]

        if data:
            json = self._json(self._patch(self._api, data=dumps(data)), 200)

        if json:
            self._update_(json)
            return True
        return False


class ReviewComment(BaseComment):
    """The :class:`ReviewComment <ReviewComment>` object. This is used to
    represent comments on pull requests.
    """
    def __init__(self, comment, session=None):
        super(ReviewComment, self).__init__(comment, session)

        #: :class:`User <github3.users.User>` who made the comment
        self.user = None
        if comment.get('user'):
            self.user = User(comment.get('user'), self)

        #: Original position inside the file
        self.original_position = comment.get('original_position')

        #: Path to the file
        self.path = comment.get('path')
        #: Position within the commit
        self.position = comment.get('position') or 0
        #: SHA of the commit the comment is on
        self.commit_id = comment.get('commit_id')

    def __repr__(self):
        return '<Review Comment [{0}]>'.format(self.user.login)
