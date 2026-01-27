#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to;
    int w;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int L, R;
    if (!(cin >> L >> R)) return 0;

    vector<vector<Edge>> g(1); // 0 unused

    auto newNode = [&]() -> int {
        g.push_back({});
        return (int)g.size() - 1;
    };

    int start = newNode(); // node 1
    int sink  = newNode(); // node 2

    auto bitlen = [&](int x) -> int {
        int l = 0;
        while (x > 0) { l++; x >>= 1; }
        if (l == 0) l = 1;
        return l;
    };

    int lenL = bitlen(L);
    int lenR = bitlen(R);

    if (lenL == 1 && lenR == 1) {
        // Only number 1 is possible
        g[start].push_back({sink, 1});
    } else {
        int maxLen = lenR;
        vector<int> F(maxLen + 1, 0);

        if (maxLen >= 2) {
            // Create free suffix states F[1..maxLen-1]
            for (int r = 1; r <= maxLen - 1; ++r) {
                F[r] = newNode();
            }
            // Build chain: from F[r] to F[r-1] (or sink)
            for (int r = 1; r <= maxLen - 1; ++r) {
                int u = F[r];
                if (r == 1) {
                    g[u].push_back({sink, 0});
                    g[u].push_back({sink, 1});
                } else {
                    g[u].push_back({F[r - 1], 0});
                    g[u].push_back({F[r - 1], 1});
                }
            }
        }

        // Mid-lengths where full range of that length is inside [L,R]
        if (lenL < lenR) {
            for (int len = lenL + 1; len <= lenR - 1; ++len) {
                int rem = len - 1;
                if (rem == 0) {
                    g[start].push_back({sink, 1});
                } else {
                    g[start].push_back({F[rem], 1});
                }
            }
        }

        auto addDP = [&](int len, int low, int high) {
            if (len == 1) {
                // Only '1'
                g[start].push_back({sink, 1});
                return;
            }

            vector<int> Lbit(len + 1), Hbit(len + 1);
            for (int i = 1; i <= len; ++i) {
                Lbit[i] = (low  >> (len - i)) & 1;
                Hbit[i] = (high >> (len - i)) & 1;
            }

            vector<vector<vector<int>>> id(len + 1,
                                           vector<vector<int>>(2, vector<int>(2, 0)));
            struct State { int pos, lt, ht; };
            queue<State> q;

            auto getNode = [&](int pos, int lt, int ht) -> int {
                if (lt == 0 && ht == 0) {
                    int rem = len - pos;
                    if (rem == 0) return sink; // should not occur
                    return F[rem];
                }
                int &cell = id[pos][lt][ht];
                if (cell) return cell;
                int node = newNode();
                cell = node;
                q.push({pos, lt, ht});
                return node;
            };

            // Initial state after first bit '1'
            int initial = getNode(1, 1, 1);
            g[start].push_back({initial, 1});

            while (!q.empty()) {
                State s = q.front(); q.pop();
                int pos = s.pos, lt = s.lt, ht = s.ht;
                int u = id[pos][lt][ht];

                for (int b = 0; b <= 1; ++b) {
                    int j = pos + 1;
                    if (lt && b < Lbit[j]) continue;
                    if (ht && b > Hbit[j]) continue;
                    if (j == len) {
                        // Last bit goes directly to sink
                        g[u].push_back({sink, b});
                    } else {
                        int lt2 = lt && (b == Lbit[j]);
                        int ht2 = ht && (b == Hbit[j]);
                        int v = getNode(j, lt2, ht2);
                        g[u].push_back({v, b});
                    }
                }
            }
        };

        if (lenL == lenR) {
            // Single length range
            addDP(lenL, L, R);
        } else {
            // lenL < lenR
            if (lenL == 1) {
                // Length-1 numbers: only '1'
                g[start].push_back({sink, 1});
            } else {
                int highL = (1 << lenL) - 1;
                addDP(lenL, L, highL);
            }
            int lowR_ = 1 << (lenR - 1);
            addDP(lenR, lowR_, R);
        }
    }

    int n = (int)g.size() - 1;
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        auto &e = g[i];
        cout << (int)e.size();
        for (auto &ed : e) {
            cout << " " << ed.to << " " << ed.w;
        }
        cout << "\n";
    }

    return 0;
}