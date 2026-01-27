#include <bits/stdc++.h>
using namespace std;

long long query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    cout.flush();
    long long d;
    if (!(cin >> d)) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        if (n <= 1) {
            cout << "! " << endl;
            cout.flush();
            continue;
        }

        const long long INF = (1LL<<62);
        vector<long long> best(n+1, INF);
        vector<int> from(n+1, -1);
        vector<char> in(n+1, 0);
        vector<tuple<int,int,long long>> edges;

        int start = 1;
        in[start] = 1;

        for (int v = 1; v <= n; ++v) {
            if (v == start) continue;
            long long d = query(start, v);
            best[v] = d;
            from[v] = start;
        }

        for (int iter = 1; iter <= n - 1; ++iter) {
            int w = -1;
            long long md = INF;
            for (int v = 1; v <= n; ++v) {
                if (!in[v] && best[v] < md) {
                    md = best[v];
                    w = v;
                }
            }
            if (w == -1) break;
            in[w] = 1;
            edges.emplace_back(from[w], w, best[w]);

            for (int v = 1; v <= n; ++v) {
                if (!in[v]) {
                    long long d = query(w, v);
                    if (d < best[v]) {
                        best[v] = d;
                        from[v] = w;
                    }
                }
            }
        }

        cout << "! ";
        for (auto &e : edges) {
            int u, v;
            long long w;
            tie(u, v, w) = e;
            cout << u << " " << v << " " << w << " ";
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}