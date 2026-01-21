#include <bits/stdc++.h>
using namespace std;

vector<vector<pair<int,int>>> g;

int newNode() {
    g.push_back({});
    return (int)g.size() - 1;
}

vector<int> getBits(int x, int len) {
    vector<int> bits(len);
    for (int i = len - 1; i >= 0; --i) {
        bits[i] = x & 1;
        x >>= 1;
    }
    return bits;
}

void build_same_length(int L, int R, int len) {
    g.assign(3, {}); // 0 unused, 1=root, 2=sink
    int root = 1, sink = 2;

    vector<int> lowBits = getBits(L, len);
    vector<int> highBits = getBits(R, len);

    vector<int> id(4 * len, 0);
    auto encode = [&](int i, int tL, int tH) {
        return (i << 2) | (tL << 1) | tH;
    };

    queue<tuple<int,int,int>> q;
    id[encode(0,1,1)] = root;
    q.emplace(0,1,1);

    while (!q.empty()) {
        auto [i, tL, tH] = q.front(); q.pop();
        int u = id[encode(i,tL,tH)];
        if (i == len) continue;
        for (int b = 0; b <= 1; ++b) {
            if (i == 0 && b == 0) continue; // no leading zero
            if (tL && b < lowBits[i]) continue;
            if (tH && b > highBits[i]) continue;
            int ntL = tL && (b == lowBits[i]);
            int ntH = tH && (b == highBits[i]);
            int v;
            if (i + 1 == len) {
                v = sink;
            } else {
                int key = encode(i + 1, ntL, ntH);
                if (id[key] == 0) {
                    id[key] = newNode();
                    q.emplace(i + 1, ntL, ntH);
                }
                v = id[key];
            }
            g[u].push_back({v, b});
        }
    }
}

void add_geq(int L, int len) {
    if (len <= 0) return;
    vector<int> bitsL = getBits(L, len);
    int root = 1, sink = 2;
    vector<int> id(2 * len, 0); // i in [0,len-1], t in {0,1}
    auto encode = [&](int i, int t) {
        return (i << 1) | t;
    };

    queue<pair<int,int>> q;
    id[encode(0,1)] = root;
    q.emplace(0,1);

    while (!q.empty()) {
        auto [i, t] = q.front(); q.pop();
        int u = id[encode(i,t)];
        if (i == len) continue;
        for (int b = 0; b <= 1; ++b) {
            if (i == 0 && b == 0) continue; // no leading zero
            if (t && b < bitsL[i]) continue;
            int nt = t ? ((b == bitsL[i]) ? 1 : 0) : 0;
            int ni = i + 1;
            int v;
            if (ni == len) {
                v = sink;
            } else {
                int key = encode(ni, nt);
                if (id[key] == 0) {
                    id[key] = newNode();
                    q.emplace(ni, nt);
                }
                v = id[key];
            }
            g[u].push_back({v, b});
        }
    }
}

void add_leq(int R, int len) {
    if (len <= 0) return;
    vector<int> bitsR = getBits(R, len);
    int root = 1, sink = 2;
    vector<int> id(2 * len, 0); // i in [0,len-1], t in {0,1}
    auto encode = [&](int i, int t) {
        return (i << 1) | t;
    };

    queue<pair<int,int>> q;
    id[encode(0,1)] = root;
    q.emplace(0,1);

    while (!q.empty()) {
        auto [i, t] = q.front(); q.pop();
        int u = id[encode(i,t)];
        if (i == len) continue;
        for (int b = 0; b <= 1; ++b) {
            if (i == 0 && b == 0) continue; // no leading zero
            if (t && b > bitsR[i]) continue;
            int nt = t ? ((b == bitsR[i]) ? 1 : 0) : 0;
            int ni = i + 1;
            int v;
            if (ni == len) {
                v = sink;
            } else {
                int key = encode(ni, nt);
                if (id[key] == 0) {
                    id[key] = newNode();
                    q.emplace(ni, nt);
                }
                v = id[key];
            }
            g[u].push_back({v, b});
        }
    }
}

void add_central(int minLen, int maxLen) {
    if (minLen > maxLen) return;
    int root = 1, sink = 2;
    int maxLenTotal = maxLen;

    vector<int> depth(maxLenTotal);
    depth[0] = root;
    for (int i = 1; i < maxLenTotal; ++i) {
        depth[i] = newNode();
    }

    for (int i = 0; i < maxLenTotal; ++i) {
        int u = depth[i];
        bool canExtend = (i < maxLenTotal - 1);
        bool canFinish = (i + 1 >= minLen);
        if (canExtend) {
            int v = depth[i + 1];
            g[u].push_back({v, 1});
            if (i > 0) {
                g[u].push_back({v, 0});
            }
        }
        if (canFinish) {
            if (i > 0) {
                g[u].push_back({sink, 0});
            }
            g[u].push_back({sink, 1});
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long Lll, Rll;
    if (!(cin >> Lll >> Rll)) return 0;
    int L = (int)Lll, R = (int)Rll;

    auto bitlen = [](long long x) {
        int len = 0;
        while (x) {
            ++len;
            x >>= 1;
        }
        return max(len, 1);
    };

    int lenL = bitlen(L);
    int lenR = bitlen(R);

    if (lenL == lenR) {
        build_same_length(L, R, lenL);
    } else {
        g.assign(3, {}); // 0 unused, 1=root, 2=sink
        add_geq(L, lenL);                 // left partial [L, 2^{lenL}-1]
        if (lenR >= lenL + 2) {
            add_central(lenL + 1, lenR - 1); // full lengths between
        }
        add_leq(R, lenR);                 // right partial [2^{lenR-1}, R]
    }

    int n = (int)g.size() - 1;
    cout << n << '\n';
    for (int i = 1; i <= n; ++i) {
        auto &adj = g[i];
        cout << (int)adj.size();
        for (auto &e : adj) {
            cout << ' ' << e.first << ' ' << e.second;
        }
        cout << '\n';
    }

    return 0;
}