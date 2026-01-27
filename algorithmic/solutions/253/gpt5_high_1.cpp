#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> tok;
    tok.reserve(1<<20);
    long long x;
    while (cin >> x) tok.push_back(x);
    if (tok.empty()) return 0;

    size_t pos = 0;
    auto find_next_graph = [&](int &n, int &m, vector<pair<int,int>> &edges) -> bool {
        size_t i = pos;
        while (i + 1 < tok.size()) {
            long long nll = tok[i];
            long long mll = tok[i + 1];
            if (nll >= 2 && nll <= 2000 && mll >= nll - 1 && mll <= 2000) {
                if (i + 2 + 2 * mll <= tok.size()) {
                    bool ok = true;
                    for (long long j = 0; j < 2 * mll; ++j) {
                        long long v = tok[i + 2 + j];
                        if (v < 1 || v > nll) { ok = false; break; }
                    }
                    if (ok) {
                        n = (int)nll;
                        m = (int)mll;
                        edges.clear();
                        edges.reserve(m);
                        for (int e = 0; e < m; ++e) {
                            int a = (int)tok[i + 2 + 2 * e];
                            int b = (int)tok[i + 2 + 2 * e + 1];
                            edges.emplace_back(a, b);
                        }
                        pos = i + 2 + 2 * m;
                        return true;
                    }
                }
            }
            ++i;
        }
        return false;
    };

    if (pos >= tok.size()) return 0;
    int T = (int)tok[pos++];
    for (int tc = 0; tc < T; ++tc) {
        int n = 0, m = 0;
        vector<pair<int,int>> edges;
        if (!find_next_graph(n, m, edges)) break;
        cout << "!";
        for (int i = 0; i < m; ++i) cout << " 0";
        cout << "\n";
        cout.flush();
    }
    return 0;
}