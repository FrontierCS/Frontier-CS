#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int S = 1 << 20;
    int idx, size;
    char buf[S];
    FastScanner(): idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, S, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T x = 0;
        c = getch(); if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) { c = getch(); if (!c) return false; }
        if (c == '-') { sign = -1; c = getch(); }
        for (; c >= '0' && c <= '9'; c = getch()) x = x * 10 + (c - '0');
        out = x * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<int> U(m), V(m);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        U[i] = u; V[i] = v;
        deg[u]++; deg[v]++;
    }

    vector<vector<int>> adj(n);
    for (int i = 0; i < n; ++i) adj[i].reserve(deg[i]);
    for (int i = 0; i < m; ++i) {
        int u = U[i], v = V[i];
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        // Any coloring is perfect
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Initial greedy coloring by decreasing degree with random tie-breaking
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){ return deg[a] > deg[b]; });

    vector<int> col(n, -1);
    for (int u : order) {
        array<int,3> cnt = {0,0,0};
        for (int v : adj[u]) if (col[v] != -1) cnt[col[v]]++;
        int best = min({cnt[0], cnt[1], cnt[2]});
        int choices[3], csz = 0;
        for (int c = 0; c < 3; ++c) if (cnt[c] == best) choices[csz++] = c;
        col[u] = choices[uniform_int_distribution<int>(0, csz - 1)(rng)];
    }

    vector<array<int,3>> ncnt(n);
    for (int i = 0; i < n; ++i) ncnt[i] = {0,0,0};
    for (int u = 0; u < n; ++u) {
        for (int v : adj[u]) {
            ncnt[u][col[v]]++;
        }
    }

    vector<int> conf(n, 0);
    long long sum_conf = 0;
    for (int u = 0; u < n; ++u) {
        conf[u] = ncnt[u][col[u]];
        sum_conf += conf[u];
    }
    long long b = sum_conf / 2;

    // Bad vertices management
    vector<int> bad;
    bad.reserve(n);
    vector<int> pos(n, -1);
    auto add_bad = [&](int v) {
        if (conf[v] > 0 && pos[v] == -1) {
            pos[v] = (int)bad.size();
            bad.push_back(v);
        }
    };
    auto remove_bad = [&](int v) {
        if (conf[v] == 0 && pos[v] != -1) {
            int i = pos[v];
            int w = bad.back();
            bad[i] = w;
            pos[w] = i;
            bad.pop_back();
            pos[v] = -1;
        }
    };
    for (int u = 0; u < n; ++u) if (conf[u] > 0) add_bad(u);

    vector<int> best_col = col;
    long long best_b = b;

    auto recolor = [&](int u, int newc) {
        int oldc = col[u];
        if (oldc == newc) return;
        int bad_old = ncnt[u][oldc];
        int bad_new = ncnt[u][newc];
        // Update neighbors
        for (int v : adj[u]) {
            ncnt[v][oldc]--;
            ncnt[v][newc]++;
            if (col[v] == oldc) {
                conf[v]--;
                if (conf[v] == 0) remove_bad(v);
            } else if (col[v] == newc) {
                int was = conf[v];
                conf[v]++;
                if (was == 0) add_bad(v);
            }
        }
        b += (long long)bad_new - bad_old;
        col[u] = newc;
        conf[u] = bad_new;
        if (conf[u] == 0) remove_bad(u);
        else add_bad(u);
    };

    const double TIME_LIMIT = 1.85; // seconds
    auto start = chrono::steady_clock::now();
    auto elapsed = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - start).count();
    };

    // Local search
    long long iter = 0;
    const double plateau_prob = 0.5;
    while (elapsed() < TIME_LIMIT) {
        if (bad.empty()) break;

        int u = bad[uniform_int_distribution<int>(0, (int)bad.size()-1)(rng)];

        // Pick best color (min conflicts)
        array<int,3> cnt = ncnt[u];
        int current_conf = conf[u];
        int cu = col[u];
        int bestCost = min({cnt[0], cnt[1], cnt[2]});

        int target = cu;
        if (bestCost < current_conf) {
            // choose one of strictly better colors
            int cands[3]; int cc = 0;
            for (int c = 0; c < 3; ++c) if (cnt[c] == bestCost) cands[cc++] = c;
            target = cands[uniform_int_distribution<int>(0, cc-1)(rng)];
        } else {
            // tie: optionally move on plateau to a different color
            int cands[3]; int cc = 0;
            for (int c = 0; c < 3; ++c) if (cnt[c] == bestCost) cands[cc++] = c;
            if (cc > 1) {
                // prefer different color with probability plateau_prob
                if (uniform_real_distribution<double>(0.0, 1.0)(rng) < plateau_prob) {
                    // pick a different color among minima
                    int idx = uniform_int_distribution<int>(0, cc-2)(rng);
                    // build list excluding cu
                    int picked = -1, j = 0;
                    for (int k = 0; k < cc; ++k) if (cands[k] != cu) {
                        if (j == idx) { picked = cands[k]; break; }
                        j++;
                    }
                    if (picked == -1) picked = cands[(uniform_int_distribution<int>(0, cc-1)(rng))];
                    target = picked;
                } else {
                    target = cu; // stay
                }
            } else {
                target = cu; // only one minimal, stay
            }
        }

        if (target != col[u]) {
            recolor(u, target);
            if (b < best_b) {
                best_b = b;
                best_col = col;
                if (best_b == 0) break;
            }
        }

        // occasional random kick to escape deep local minima
        if ((++iter & 8191) == 0 && !bad.empty() && elapsed() < TIME_LIMIT) {
            int x = bad[uniform_int_distribution<int>(0, (int)bad.size()-1)(rng)];
            int newc = col[x];
            for (int tries = 0; tries < 2 && newc == col[x]; ++tries)
                newc = uniform_int_distribution<int>(0,2)(rng);
            if (newc != col[x]) {
                recolor(x, newc);
                if (b < best_b) {
                    best_b = b;
                    best_col = col;
                    if (best_b == 0) break;
                }
            }
        }

        if ((iter & 1023) == 0 && elapsed() >= TIME_LIMIT) break;
    }

    const vector<int> &ans = (best_b <= b ? best_col : col);
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (ans[i] + 1);
    }
    cout << '\n';
    return 0;
}