#include <bits/stdc++.h>
using namespace std;

static const int MAX_K = 1000;
int n;
int query_count = 0;

long long ask(const vector<int>& arr) {
    cout << 0 << ' ' << arr.size();
    for (int x : arr) cout << ' ' << x;
    cout << endl;
    cout.flush();
    long long ans;
    if (!(cin >> ans)) exit(0);
    query_count++;
    return ans;
}

// Returns number of indices j in subset for which s[a] != s[j]
// Uses pattern per j: [a, j, j, a, a], which contributes 1 iff s[a]!=s[j], 0 otherwise.
// No cross-pair contributions due to separators.
long long askOppositeCount(int a, const vector<int>& subset) {
    vector<int> arr;
    arr.reserve(5 * subset.size());
    for (int j : subset) {
        arr.push_back(a);
        arr.push_back(j);
        arr.push_back(j);
        arr.push_back(a);
        arr.push_back(a);
    }
    return ask(arr);
}

// For a group of indices, returns sum over i in group of (s[i]=='(') * (2^pos(i))
// Uses known close_idx as ')' anchor; optionally uses open_idx as '(' filler at end.
long long askGroupSumOpen(const vector<int>& group, int close_idx, int open_idx) {
    vector<int> arr;
    int m = (int)group.size();
    // One close at start for safety
    arr.push_back(close_idx);
    for (int p = 0; p < m; ++p) {
        int i = group[p];
        int w = 1 << p;
        for (int r = 0; r < w; ++r) {
            arr.push_back(i);
            arr.push_back(close_idx);
            arr.push_back(close_idx);
        }
    }
    // One open at end for safety
    arr.push_back(open_idx);
    return ask(arr);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    // Find an index with opposite type to index 1 using chunking + binary search within chunk
    vector<int> rest;
    for (int i = 2; i <= n; ++i) rest.push_back(i);

    const int CHUNK = 200;
    vector<int> candidateChunk;
    for (int i = 0; i < (int)rest.size(); i += CHUNK) {
        int r = min(i + CHUNK, (int)rest.size());
        vector<int> chunk(rest.begin() + i, rest.begin() + r);
        long long val = askOppositeCount(1, chunk);
        if (val > 0) {
            candidateChunk = chunk;
            break;
        }
    }
    // Binary search within the found chunk to pinpoint one opposite index
    while ((int)candidateChunk.size() > 1) {
        int mid = (int)candidateChunk.size() / 2;
        vector<int> left(candidateChunk.begin(), candidateChunk.begin() + mid);
        long long val = askOppositeCount(1, left);
        if (val > 0) {
            candidateChunk = left;
        } else {
            vector<int> right(candidateChunk.begin() + mid, candidateChunk.end());
            candidateChunk = right;
        }
    }
    int oppIdx = candidateChunk.empty() ? 2 : candidateChunk[0]; // Fallback, though candidateChunk should not be empty.

    // Determine which is '(' and which is ')'
    long long pairRes = ask({1, oppIdx});
    int open_idx, close_idx;
    if (pairRes == 1) {
        open_idx = 1;
        close_idx = oppIdx;
    } else {
        open_idx = oppIdx;
        close_idx = 1;
    }

    // Classify all indices in groups of size up to 8 using binary-weighted encoding
    const int G = 8;
    vector<char> s(n + 1, ')'); // default to ')', will set '(' where needed
    for (int i = 1; i <= n; i += G) {
        int r = min(n, i + G - 1);
        vector<int> group;
        for (int j = i; j <= r; ++j) group.push_back(j);
        long long val = askGroupSumOpen(group, close_idx, open_idx);
        for (int p = 0; p < (int)group.size(); ++p) {
            if (val & (1LL << p)) s[group[p]] = '(';
            else s[group[p]] = ')';
        }
    }

    string res;
    res.reserve(n);
    for (int i = 1; i <= n; ++i) res.push_back(s[i]);

    cout << 1 << ' ' << res << endl;
    cout.flush();

    return 0;
}