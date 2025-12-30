#include <bits/stdc++.h>
using namespace std;

struct Parser {
    string s;
    size_t pos;
    Parser(string input) : s(move(input)), pos(0) {}

    void skipSpaces() {
        while (pos < s.size() && isspace(static_cast<unsigned char>(s[pos]))) pos++;
    }

    bool parseInt(long long &out) {
        skipSpaces();
        if (pos >= s.size()) return false;
        bool neg = false;
        if (s[pos] == '+' || s[pos] == '-') {
            neg = (s[pos] == '-');
            pos++;
        }
        if (pos >= s.size() || !isdigit(static_cast<unsigned char>(s[pos]))) return false;
        long long val = 0;
        while (pos < s.size() && isdigit(static_cast<unsigned char>(s[pos]))) {
            val = val * 10 + (s[pos] - '0');
            pos++;
        }
        out = neg ? -val : val;
        return true;
    }

    bool parseAdjacencyMatrix(int n, vector<vector<int>> &adj) {
        size_t pos0 = pos;
        vector<int> bits;
        bits.reserve(n * n);
        for (int i = 0; i < n * n; ++i) {
            skipSpaces();
            if (pos >= s.size() || (s[pos] != '0' && s[pos] != '1')) {
                pos = pos0;
                return false;
            }
            bits.push_back(s[pos] - '0');
            pos++;
        }
        adj.assign(n, vector<int>(n, 0));
        int idx = 0;
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                adj[i][j] = bits[idx++];
        return true;
    }

    bool parseEdgeList(int n, vector<vector<int>> &adj) {
        size_t pos0 = pos;
        long long m;
        if (!parseInt(m)) {
            pos = pos0;
            return false;
        }
        if (m < 0 || m > 1LL * n * (n - 1) / 2) {
            pos = pos0;
            return false;
        }
        adj.assign(n, vector<int>(n, 0));
        for (long long i = 0; i < m; ++i) {
            long long u, v;
            if (!parseInt(u) || !parseInt(v)) {
                pos = pos0;
                return false;
            }
            if (u < 1 || u > n || v < 1 || v > n || u == v) continue;
            adj[u - 1][v - 1] = adj[v - 1][u - 1] = 1;
        }
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire input into a string for flexible parsing
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    Parser parser(input);

    long long Tll;
    if (!parser.parseInt(Tll)) return 0;
    int T = (int)Tll;

    vector<int> results;
    results.reserve(T);

    for (int tc = 0; tc < T; ++tc) {
        long long nll;
        if (!parser.parseInt(nll)) {
            // If input is malformed, assume no further testcases
            break;
        }
        int n = (int)nll;
        vector<vector<int>> adj;

        // Try to parse adjacency matrix; if not, try edge list
        if (!parser.parseAdjacencyMatrix(n, adj)) {
            if (!parser.parseEdgeList(n, adj)) {
                // Fallback: empty graph
                adj.assign(n, vector<int>(n, 0));
            }
        }

        // Check connectivity via BFS/DFS
        vector<int> vis(n, 0);
        queue<int> q;
        vis[0] = 1;
        q.push(0);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v = 0; v < n; ++v) {
                if (u != v && adj[u][v] && !vis[v]) {
                    vis[v] = 1;
                    q.push(v);
                }
            }
        }
        bool connected = true;
        for (int i = 0; i < n; ++i) if (!vis[i]) { connected = false; break; }
        results.push_back(connected ? 1 : 0);
    }

    for (int i = 0; i < (int)results.size(); ++i) {
        cout << results[i] << (i + 1 == (int)results.size() ? '\n' : '\n');
    }

    return 0;
}