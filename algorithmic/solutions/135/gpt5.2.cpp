#include <bits/stdc++.h>
using namespace std;

static int K = 0, N = 0;
static int queryCount = 0;

static inline bool hasPair(const vector<pair<int,int>>& pairs, int u, int v) {
    if (u > v) swap(u, v);
    for (auto [a,b] : pairs) if (a == u && b == v) return true;
    return false;
}

static vector<pair<int,int>> ask(int x, int y, int z) {
    if (++queryCount > K) {
        // Exceeded query limit; terminate.
        exit(0);
    }
    cout << "? " << x << " " << y << " " << z << "\n";
    cout.flush();

    int r;
    if (!(cin >> r)) exit(0);
    if (r < 0) exit(0);

    vector<pair<int,int>> pairs;
    pairs.reserve(r);
    for (int i = 0; i < r; i++) {
        int a, b;
        cin >> a >> b;
        if (a > b) swap(a, b);
        pairs.push_back({a, b});
    }
    return pairs;
}

static inline int signCloser(const vector<pair<int,int>>& ans, int A, int B, int v) {
    // returns:
    // 0 if v closer to A, 1 if v closer to B, 2 if tie, 3 if undefined (AB closest only)
    bool Av = hasPair(ans, A, v);
    bool Bv = hasPair(ans, B, v);
    if (Av && !Bv) return 0;
    if (Bv && !Av) return 1;
    if (Av && Bv) return 2;
    return 3;
}

static vector<int> traverseCycle(int p, int startNeighbor,
                                const vector<vector<int>>& cand) {
    vector<int> order;
    order.reserve(N);
    vector<char> vis(N, 0);

    order.push_back(p);
    order.push_back(startNeighbor);
    vis[p] = 1;
    vis[startNeighbor] = 1;

    int prev = p, cur = startNeighbor;

    while ((int)order.size() < N) {
        int nxt = -1;

        // Try candidate list
        for (int x : cand[cur]) {
            if (x == prev || x == cur || vis[x]) continue;
            auto ans = ask(cur, prev, x);
            if (hasPair(ans, cur, x)) { nxt = x; break; }
        }

        // Fallback: scan all unvisited vertices (expensive; should be rare)
        if (nxt == -1) {
            for (int x = 0; x < N; x++) {
                if (x == prev || x == cur || vis[x]) continue;
                auto ans = ask(cur, prev, x);
                if (hasPair(ans, cur, x)) { nxt = x; break; }
            }
        }

        if (nxt == -1) break;

        order.push_back(nxt);
        vis[nxt] = 1;
        prev = cur;
        cur = nxt;
    }

    return order;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> K >> N;
    if (!cin) return 0;

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    int p = 0;

    // Find one neighbor 'a' of p using a safe tournament.
    int a = -1;
    for (int i = 0; i < N; i++) if (i != p) { a = i; break; }
    for (int v = 0; v < N; v++) {
        if (v == p || v == a) continue;
        auto ans = ask(p, a, v);
        bool pa = hasPair(ans, p, a);
        bool pv = hasPair(ans, p, v);
        if (pv && !pa) a = v;
    }

    // Find the other neighbor 'b' of p by scanning.
    int b = -1;
    for (int v = 0; v < N; v++) {
        if (v == p || v == a) continue;
        auto ans = ask(p, a, v);
        if (hasPair(ans, p, v)) { b = v; break; }
    }
    if (b == -1) {
        // Fallback for extremely unlikely I/O anomalies.
        b = (a == 1 ? 2 : 1);
        if (b == p) b = (b + 1) % N;
    }

    // Build far-ish pairs for signatures.
    int M = 12;
    int TESTS = 10;
    vector<pair<int,int>> poles;
    poles.reserve(M);

    auto pickDistinct = [&](int avoid1, int avoid2) -> int {
        for (int it = 0; it < 1000; it++) {
            int x = (int)(rng() % N);
            if (x != avoid1 && x != avoid2) return x;
        }
        for (int x = 0; x < N; x++) if (x != avoid1 && x != avoid2) return x;
        return 0;
    };

    auto isBadPair = [&](int A, int B) -> bool {
        for (int t = 0; t < TESTS; t++) {
            int x = pickDistinct(A, B);
            auto ans = ask(A, B, x);
            if (hasPair(ans, A, B)) return true;
        }
        return false;
    };

    int attempts = 0;
    while ((int)poles.size() < M && attempts < 600) {
        attempts++;
        int A = (int)(rng() % N);
        int B = (int)(rng() % N);
        if (A == B) continue;
        bool dup = false;
        for (auto [u,v] : poles) {
            if ((u == A && v == B) || (u == B && v == A)) { dup = true; break; }
        }
        if (dup) continue;

        if (!isBadPair(A, B)) poles.push_back({A, B});
    }
    while ((int)poles.size() < M) {
        int A = (int)(rng() % N);
        int B = (int)(rng() % N);
        if (A == B) continue;
        poles.push_back({A, B});
    }

    // Compute signatures
    vector<vector<uint8_t>> sig(N, vector<uint8_t>(M, 3));
    for (int i = 0; i < M; i++) {
        int A = poles[i].first;
        int B = poles[i].second;
        for (int v = 0; v < N; v++) {
            if (v == A) { sig[v][i] = 0; continue; }
            if (v == B) { sig[v][i] = 1; continue; }
            auto ans = ask(A, B, v);
            sig[v][i] = (uint8_t)signCloser(ans, A, B, v);
        }
    }

    // Build candidate lists by signature similarity
    int T = 40;
    vector<vector<int>> cand(N);
    cand.assign(N, {});
    for (int u = 0; u < N; u++) {
        vector<pair<pair<int,int>, int>> vec;
        vec.reserve(N-1);
        for (int v = 0; v < N; v++) {
            if (v == u) continue;
            int diffs = 0, common = 0;
            for (int i = 0; i < M; i++) {
                uint8_t su = sig[u][i], sv = sig[v][i];
                if (su == 3 || sv == 3) continue;
                common++;
                if (su != sv) diffs++;
            }
            if (common == 0) diffs = M + 5;
            vec.push_back({{diffs, -common}, v});
        }
        int keep = min(T, (int)vec.size());
        nth_element(vec.begin(), vec.begin() + keep, vec.end(),
                    [&](auto &L, auto &R) { return L.first < R.first; });
        vec.resize(keep);
        sort(vec.begin(), vec.end(), [&](auto &L, auto &R) { return L.first < R.first; });
        cand[u].reserve(keep);
        for (auto &e : vec) cand[u].push_back(e.second);
    }

    // Try traversal from neighbor a, if fails try neighbor b.
    vector<int> order = traverseCycle(p, a, cand);
    if ((int)order.size() != N) {
        order = traverseCycle(p, b, cand);
    }

    // Final output
    cout << "!";
    for (int x : order) cout << " " << x;
    cout << "\n";
    cout.flush();
    return 0;
}