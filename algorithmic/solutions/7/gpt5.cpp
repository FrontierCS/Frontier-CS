#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to, w;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long L, R;
    if (!(cin >> L >> R)) return 0;
    
    vector<vector<Edge>> g(1); // 1-based indexing, g[0] unused
    auto newNode = [&]() {
        g.push_back({});
        return (int)g.size() - 1;
    };
    auto addEdge = [&](int u, int v, int w) {
        g[u].push_back({v, w});
    };
    auto bitlen = [&](long long x)->int {
        int l = 0;
        while (x) { l++; x >>= 1; }
        if (l == 0) l = 1;
        return l;
    };
    
    int start = newNode();
    
    // Lazy creation of T_i chain nodes: T[i] allows any i-bit suffix.
    vector<int> T(1, -1); // T[0] may be created on demand
    function<int(int)> getT = [&](int i)->int {
        if ((int)T.size() <= i) T.resize(i + 1, -1);
        if (T[i] != -1) return T[i];
        if (i == 0) {
            int id = newNode(); // sink with outdegree 0
            T[0] = id;
            return id;
        } else {
            int prev = getT(i - 1);
            int id = newNode();
            T[i] = id;
            addEdge(id, prev, 0);
            addEdge(id, prev, 1);
            return id;
        }
    };
    
    int lenL = bitlen(L);
    int lenR = bitlen(R);
    
    unordered_set<int> startTargets; // avoid duplicate start->(1)->target edges
    auto addStartEdge1 = [&](int target) {
        if (!startTargets.count(target)) {
            startTargets.insert(target);
            addEdge(start, target, 1);
        }
    };
    
    if (lenL == lenR) {
        int len = lenR;
        if (len == 1) {
            // Only number is 1
            addStartEdge1(getT(0));
        } else {
            // Combined DP with both bounds tightness
            int maxI = len - 2; // positions i from len-2 down to 0 after consuming first '1'
            vector<vector<vector<int>>> id(maxI + 1, vector<vector<int>>(2, vector<int>(2, 0)));
            function<int(int,int,int)> build = [&](int i, int tL, int tU)->int {
                int &ref = id[i][tL][tU];
                if (ref) return ref;
                int node = newNode();
                ref = node;
                for (int b = 0; b <= 1; ++b) {
                    if (tL && b < ((L >> i) & 1)) continue;
                    if (tU && b > ((R >> i) & 1)) continue;
                    int dest;
                    if (i == 0) {
                        dest = getT(0);
                    } else {
                        int nL = tL && (b == ((L >> i) & 1));
                        int nU = tU && (b == ((R >> i) & 1));
                        if (!nL && !nU) dest = getT(i);
                        else dest = build(i - 1, nL, nU);
                    }
                    addEdge(node, dest, b);
                }
                return node;
            };
            int initial = build(len - 2, 1, 1);
            addStartEdge1(initial);
        }
    } else {
        // lenL < lenR
        // Length lenL: numbers >= L
        if (lenL == 1) {
            addStartEdge1(getT(0)); // only number 1
        } else {
            int k = lenL - 1;
            vector<int> LL(k);
            for (int pos = k - 1; pos >= 0; --pos) {
                LL[pos] = newNode();
            }
            for (int pos = k - 1; pos >= 0; --pos) {
                int next = (pos > 0 ? LL[pos - 1] : getT(0));
                int lb = (L >> pos) & 1;
                if (lb == 0) {
                    addEdge(LL[pos], next, 0);
                    addEdge(LL[pos], getT(pos), 1);
                } else {
                    addEdge(LL[pos], next, 1);
                }
            }
            addStartEdge1(LL[k - 1]);
        }
        // Full lengths between
        for (int len = lenL + 1; len <= lenR - 1; ++len) {
            addStartEdge1(getT(len - 1));
        }
        // Length lenR: numbers <= R
        if (lenR >= 2) {
            int k = lenR - 1;
            vector<int> UR(k);
            for (int pos = k - 1; pos >= 0; --pos) {
                UR[pos] = newNode();
            }
            for (int pos = k - 1; pos >= 0; --pos) {
                int next = (pos > 0 ? UR[pos - 1] : getT(0));
                int rb = (R >> pos) & 1;
                if (rb == 1) {
                    addEdge(UR[pos], next, 1);
                    addEdge(UR[pos], getT(pos), 0);
                } else {
                    addEdge(UR[pos], next, 0);
                }
            }
            addStartEdge1(UR[k - 1]);
        }
    }
    
    cout << (int)g.size() - 1 << "\n";
    for (int i = 1; i < (int)g.size(); ++i) {
        cout << (int)g[i].size();
        for (auto &e : g[i]) {
            cout << " " << e.to << " " << e.w;
        }
        cout << "\n";
    }
    return 0;
}