#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool next(T &out) {
        char c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        T sign = 1;
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        long long val = 0;
        while (c >= '0' && c <= '9') {
            val = val * 10 + (c - '0');
            c = getChar();
        }
        out = (T)(val * sign);
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;

    int T;
    if (!fs.next(T)) return 0;

    for (int tc = 0; tc < T; ++tc) {
        int n;
        if (!fs.next(n)) return 0;

        long long m = 1LL * n * (n - 1) / 2;
        vector<int> H;
        H.reserve((size_t)m);
        for (long long i = 0; i < m; ++i) {
            int x;
            fs.next(x);
            H.push_back(x);
        }

        vector<long long> base(n + 2, 0);
        for (int i = 2; i <= n; ++i) base[i] = base[i - 1] + (n - (i - 1));

        auto getD = [&](int a, int b) -> long long {
            if (a == b) return 0;
            if (a > b) swap(a, b);
            long long idx = base[a] + (b - a - 1);
            return H[(size_t)idx];
        };

        vector<long long> dist(n + 1, 0);
        for (int i = 2; i <= n; ++i) dist[i] = getD(1, i);

        vector<int> order(n);
        iota(order.begin(), order.end(), 1);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (dist[a] != dist[b]) return dist[a] < dist[b];
            return a < b;
        });

        vector<char> processed(n + 1, 0);
        processed[order[0]] = 1; // root

        vector<tuple<int,int,long long>> edges;
        edges.reserve(n ? n - 1 : 0);

        for (int k = 1; k < n; ++k) {
            int v = order[k];
            long long bestDist = -1;
            int best = order[0]; // default to root
            for (int j = 0; j < k; ++j) {
                int u = order[j];
                if (!processed[u]) continue;
                long long duv = getD(u, v);
                if (duv == dist[v] - dist[u]) {
                    if (dist[u] > bestDist) {
                        bestDist = dist[u];
                        best = u;
                    }
                }
            }
            long long w = getD(best, v);
            edges.emplace_back(best, v, w);
            processed[v] = 1;
        }

        if (n == 1) {
            cout << "\n";
        } else {
            for (auto &e : edges) {
                int u, v;
                long long w;
                tie(u, v, w) = e;
                cout << u << " " << v << " " << w << "\n";
            }
        }
    }

    return 0;
}