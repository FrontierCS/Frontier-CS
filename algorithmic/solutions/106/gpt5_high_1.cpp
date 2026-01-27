#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) {
        return 0;
    }
    
    // Read the rest of input as lines
    string dummy;
    getline(cin, dummy); // consume endline after n
    vector<string> lines;
    string line;
    while (getline(cin, line)) {
        lines.push_back(line);
    }
    
    auto trim = [&](const string &s) {
        string r;
        for (char c : s) if (!isspace((unsigned char)c)) r.push_back(c);
        return r;
    };
    
    // Graph representation
    vector<vector<int>> g(n + 1);
    vector<vector<char>> has(n + 1, vector<char>(n + 1, 0));
    auto addEdge = [&](int u, int v) {
        if (u < 1 || v < 1 || u > n || v > n) return;
        if (u == v) return;
        if (!has[u][v]) {
            has[u][v] = has[v][u] = 1;
            g[u].push_back(v);
            g[v].push_back(u);
        }
    };
    
    bool built = false;
    
    // Try parse adjacency matrix from lines of 0/1 (without spaces or with spaces)
    if (!built && (int)lines.size() >= n) {
        vector<string> rows(n);
        bool ok = true;
        for (int i = 0; i < n; i++) {
            string bits;
            for (char c : lines[i]) {
                if (c == '0' || c == '1') bits.push_back(c);
                else if (isspace((unsigned char)c)) continue;
                else { ok = false; break; }
            }
            if (!ok) break;
            if ((int)bits.size() != n) { ok = false; break; }
            rows[i] = bits;
        }
        if (ok) {
            for (int i = 0; i < n; i++) {
                for (int j = i + 1; j < n; j++) {
                    if ((rows[i][j] == '1') || (rows[j][i] == '1')) addEdge(i + 1, j + 1);
                }
            }
            built = true;
        }
    }
    
    // Gather all integer tokens
    vector<long long> toks;
    {
        for (const string &L : lines) {
            istringstream iss(L);
            long long x;
            while (iss >> x) toks.push_back(x);
        }
    }
    
    auto all01 = [&](const vector<long long>& v) {
        for (auto x : v) if (!(x == 0 || x == 1)) return false;
        return true;
    };
    
    // Try matrix tokens n*n
    if (!built && (int)toks.size() == n *  n && all01(toks)) {
        int p = 0;
        vector<vector<int>> mat(n, vector<int>(n, 0));
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                mat[i][j] = (int)toks[p++];
        for (int i = 0; i < n; i++)
            for (int j = i + 1; j < n; j++)
                if (mat[i][j] || mat[j][i]) addEdge(i + 1, j + 1);
        built = true;
    }
    
    // Try triangular tokens n*(n-1)/2
    if (!built && (int)toks.size() == n * (n - 1) / 2 && all01(toks)) {
        int p = 0;
        for (int i = 1; i <= n; i++) {
            for (int j = i + 1; j <= n; j++) {
                if (toks[p++] != 0) addEdge(i, j);
            }
        }
        built = true;
    }
    
    // Try edges list with m followed by 2m ints
    if (!built && !toks.empty()) {
        long long m = toks[0];
        if ((long long)toks.size() == 1 + 2 * m) {
            for (long long i = 0; i < m; i++) {
                int u = (int)toks[1 + 2 * i];
                int v = (int)toks[1 + 2 * i + 1];
                addEdge(u, v);
            }
            built = true;
        }
    }
    
    // Try plain pairs
    if (!built && (toks.size() % 2 == 0) && !toks.empty()) {
        int m = (int)toks.size() / 2;
        for (int i = 0; i < m; i++) {
            int u = (int)toks[2 * i];
            int v = (int)toks[2 * i + 1];
            addEdge(u, v);
        }
        built = true;
    }
    
    // If still not built, assume empty graph
    if (!built) {
        // g is already empty
    }
    
    // Now, determine bipartiteness and produce either partition or odd cycle
    vector<int> color(n + 1, -1), parent(n + 1, -1), depth(n + 1, 0);
    
    auto build_cycle = [&](int u, int v) {
        vector<int> pathU, pathV;
        int a = u, b = v;
        while (depth[a] > depth[b]) {
            pathU.push_back(a);
            a = parent[a];
        }
        while (depth[b] > depth[a]) {
            pathV.push_back(b);
            b = parent[b];
        }
        while (a != b) {
            pathU.push_back(a);
            pathV.push_back(b);
            a = parent[a];
            b = parent[b];
        }
        pathU.push_back(a); // LCA
        
        vector<int> cycle = pathU;
        reverse(pathV.begin(), pathV.end());
        for (int x : pathV) cycle.push_back(x);
        // cycle endpoints are u and v; the closing edge (v,u) exists
        return cycle;
    };
    
    bool bip = true;
    vector<int> cycle_ans;
    for (int s = 1; s <= n && bip; s++) {
        if (color[s] != -1) continue;
        queue<int> q;
        color[s] = 0;
        parent[s] = -1;
        depth[s] = 0;
        q.push(s);
        while (!q.empty() && bip) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (color[v] == -1) {
                    color[v] = color[u] ^ 1;
                    parent[v] = u;
                    depth[v] = depth[u] + 1;
                    q.push(v);
                } else if (v != parent[u] && color[v] == color[u]) {
                    // Found odd cycle
                    cycle_ans = build_cycle(u, v);
                    bip = false;
                    break;
                }
            }
        }
    }
    
    if (bip) {
        vector<int> part;
        for (int i = 1; i <= n; i++) {
            if (color[i] == -1) color[i] = 0; // isolated vertex
            if (color[i] == 0) part.push_back(i);
        }
        cout << "Y " << part.size() << "\n";
        for (size_t i = 0; i < part.size(); i++) {
            if (i) cout << ' ';
            cout << part[i];
        }
        cout << "\n";
    } else {
        cout << "N " << cycle_ans.size() << "\n";
        for (size_t i = 0; i < cycle_ans.size(); i++) {
            if (i) cout << ' ';
            cout << cycle_ans[i];
        }
        cout << "\n";
    }
    
    return 0;
}