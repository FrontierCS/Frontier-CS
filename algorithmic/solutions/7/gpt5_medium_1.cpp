#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long L, R;
    if (!(cin >> L >> R)) return 0;

    auto toBits = [](long long x) {
        vector<int> b;
        while (x > 0) {
            b.push_back(int(x & 1));
            x >>= 1;
        }
        reverse(b.begin(), b.end());
        if (b.empty()) b.push_back(0);
        return b;
    };

    vector<int> bL = toBits(L);
    vector<int> bR = toBits(R);
    int lenL = (int)bL.size();
    int lenR = (int)bR.size();

    // Graph storage 1-based
    int n = 0;
    vector<vector<pair<int,int>>> adj(1); // adj[0] unused
    auto newNode = [&]() {
        adj.emplace_back();
        return ++n;
    };
    auto addEdge = [&](int u, int v, int w) {
        adj[u].push_back({v, w});
    };

    int start = newNode(); // node 1 is start

    // Build D nodes: D[0] is end (only outdeg 0 node), D[d] for d>=1 has two edges (0,1) -> D[d-1]
    vector<int> D(max(1, lenR), -1);
    D[0] = newNode(); // end node
    for (int d = 1; d <= lenR - 1; ++d) {
        D[d] = newNode();
        addEdge(D[d], D[d-1], 0);
        addEdge(D[d], D[d-1], 1);
    }

    if (lenL == lenR) {
        int nLen = lenR;
        // States: (i, eqL, eqR), with i in [0..nLen)
        // Map to node ids; start corresponds to (0,1,1)
        vector<vector<vector<int>>> id(nLen+1, vector<vector<int>>(2, vector<int>(2, -1)));
        vector<vector<vector<char>>> vis(nLen+1, vector<vector<char>>(2, vector<char>(2, 0)));

        auto getId = [&](int i, int eqL, int eqR) -> int {
            if (i == 0 && eqL == 1 && eqR == 1) return start;
            int &ref = id[i][eqL][eqR];
            if (ref == -1) ref = newNode();
            return ref;
        };

        queue<tuple<int,int,int>> q;
        vis[0][1][1] = 1;
        q.emplace(0,1,1);

        while (!q.empty()) {
            auto [i, eqL, eqR] = q.front(); q.pop();
            int u = getId(i, eqL, eqR);
            for (int b = 0; b <= 1; ++b) {
                // no leading zero
                if (i == 0 && b == 0) continue;
                if (eqL && b < bL[i]) continue;
                if (eqR && b > bR[i]) continue;
                int neL = eqL && (b == bL[i]);
                int neR = eqR && (b == bR[i]);
                if (i + 1 == nLen) {
                    addEdge(u, D[0], b);
                } else if (!neL && !neR) {
                    int rem = nLen - (i + 1);
                    addEdge(u, D[rem], b);
                } else {
                    int v = getId(i + 1, neL, neR);
                    addEdge(u, v, b);
                    if (!vis[i + 1][neL][neR]) {
                        vis[i + 1][neL][neR] = 1;
                        q.emplace(i + 1, neL, neR);
                    }
                }
            }
        }
    } else {
        // lenL < lenR
        // Lower-bound-only automaton for length lenL (>= L)
        if (lenL >= 1) {
            vector<int> idLower(max(1, lenL), -1); // for i=1..lenL-1
            auto getLowerId = [&](int i) -> int {
                if (i == 0) return start;
                if (idLower[i] == -1) idLower[i] = newNode();
                return idLower[i];
            };
            for (int i = 0; i < lenL; ++i) {
                int u = getLowerId(i);
                int bitL = bL[i];
                for (int b = 0; b <= 1; ++b) {
                    if (i == 0 && b == 0) continue; // no leading zero
                    if (b < bitL) continue;
                    if (b == bitL) {
                        if (i + 1 == lenL) addEdge(u, D[0], b);
                        else addEdge(u, getLowerId(i + 1), b);
                    } else { // b > bitL -> only possible when bitL==0 and b==1
                        int rem = lenL - (i + 1);
                        addEdge(u, D[rem], b);
                    }
                }
            }
        }

        // Upper-bound-only automaton for length lenR (<= R)
        if (lenR >= 1) {
            vector<int> idUpper(max(1, lenR), -1); // for i=1..lenR-1
            auto getUpperId = [&](int i) -> int {
                if (i == 0) return start;
                if (idUpper[i] == -1) idUpper[i] = newNode();
                return idUpper[i];
            };
            for (int i = 0; i < lenR; ++i) {
                int u = getUpperId(i);
                int bitR = bR[i];
                for (int b = 0; b <= 1; ++b) {
                    if (i == 0 && b == 0) continue; // no leading zero
                    if (b > bitR) continue;
                    if (b == bitR) {
                        if (i + 1 == lenR) addEdge(u, D[0], b);
                        else addEdge(u, getUpperId(i + 1), b);
                    } else { // b < bitR -> only when bitR==1 and b==0
                        int rem = lenR - (i + 1);
                        addEdge(u, D[rem], b);
                    }
                }
            }
        }

        // Interior lengths: len in (lenL, lenR)
        for (int nlen = lenL + 1; nlen <= lenR - 1; ++nlen) {
            // path: start --1--> D[nlen-1], then any bits
            addEdge(start, D[nlen - 1], 1);
        }
    }

    // Output
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        cout << (int)adj[i].size();
        for (auto &e : adj[i]) {
            cout << " " << e.first << " " << e.second;
        }
        cout << "\n";
    }
    return 0;
}