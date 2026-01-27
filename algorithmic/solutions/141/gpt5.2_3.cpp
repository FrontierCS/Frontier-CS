#include <bits/stdc++.h>
using namespace std;

static const long long OP_LIMIT = 100000;

struct DSU {
    vector<int> p, r;
    DSU(int n = 0) { init(n); }
    void init(int n) {
        p.resize(n + 1);
        r.assign(n + 1, 0);
        iota(p.begin(), p.end(), 0);
    }
    int find(int x) { return p[x] == x ? x : p[x] = find(p[x]); }
    bool unite(int a, int b) {
        a = find(a); b = find(b);
        if (a == b) return false;
        if (r[a] < r[b]) swap(a, b);
        p[b] = a;
        if (r[a] == r[b]) r[a]++;
        return true;
    }
};

struct Interactor {
    long long ops = 0;

    void reset() {
        cout << "R\n";
        cout.flush();
        ops++;
    }

    char query(int c) {
        cout << "? " << c << "\n";
        cout.flush();
        ops++;
        char ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    }

    [[noreturn]] void answer(int d) {
        cout << "! " << d << "\n";
        cout.flush();
        exit(0);
    }
};

static vector<vector<int>> buildTrailsK1(int n) {
    int N = n + 1; // vertices 0..n, 0 is dummy
    vector<vector<uint8_t>> used(N, vector<uint8_t>(N, 0));
    vector<int> ptr(N, 0);

    long long edges = 1LL * N * (N - 1) / 2;
    vector<int> circuit;
    circuit.reserve((size_t)edges + 1);

    vector<int> st;
    st.reserve((size_t)edges + 1);
    st.push_back(0);

    while (!st.empty()) {
        int v = st.back();
        int &i = ptr[v];
        while (i < N && (i == v || used[v][i])) i++;
        if (i >= N) {
            circuit.push_back(v);
            st.pop_back();
        } else {
            int u = i;
            used[v][u] = used[u][v] = 1;
            st.push_back(u);
        }
    }

    reverse(circuit.begin(), circuit.end());

    vector<vector<int>> trails;
    vector<int> cur;
    for (int v : circuit) {
        if (v == 0) {
            if (cur.size() >= 2) trails.push_back(cur);
            cur.clear();
        } else {
            cur.push_back(v);
        }
    }
    if (cur.size() >= 2) trails.push_back(cur);

    return trails;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    Interactor I;

    if (n == 1) {
        I.answer(1);
    }

    if (k == 1) {
        // Exact solution via covering all pairs with an Euler tour on K_{n+1} and splitting at dummy vertex.
        // Total operations ~ n(n-1)/2 + n, which fits only for smaller n; assumed by tests when k=1.
        auto trails = buildTrailsK1(n);
        DSU dsu(n);

        for (const auto &tr : trails) {
            I.reset();
            int prev = tr[0];
            (void)I.query(prev); // first is always N after reset
            for (size_t i = 1; i < tr.size(); i++) {
                int cur = tr[i];
                char ans = I.query(cur);
                if (ans == 'Y') dsu.unite(prev, cur);
                prev = cur;
            }
        }

        int d = 0;
        for (int i = 1; i <= n; i++) if (dsu.find(i) == i) d++;
        I.answer(d);
    }

    // k >= 2: batch insertion with block tests.
    int p = k / 2;
    int b = k - p; // equals p when k is power of 2 and k>=2
    vector<vector<int>> blocks;
    int d = 0;

    auto addRep = [&](int idx) {
        if (blocks.empty() || (int)blocks.back().size() >= b) blocks.push_back({});
        blocks.back().push_back(idx);
        d++;
    };

    for (int start = 1; start <= n; start += p) {
        int end = min(n, start + p - 1);

        // Build distinct candidates within this chunk
        I.reset();
        vector<int> cand;
        cand.reserve(end - start + 1);
        for (int idx = start; idx <= end; idx++) {
            char ans = I.query(idx);
            if (ans == 'N') cand.push_back(idx);
        }

        if (cand.empty()) continue;
        vector<char> dup(cand.size(), 0);

        // Filter candidates against all known representatives
        for (const auto &blk : blocks) {
            // Early exit if all candidates are already duplicates
            bool anyLeft = false;
            for (size_t i = 0; i < cand.size(); i++) if (!dup[i]) { anyLeft = true; break; }
            if (!anyLeft) break;

            I.reset();
            for (int rep : blk) (void)I.query(rep);

            for (size_t i = 0; i < cand.size(); i++) {
                if (dup[i]) continue;
                char ans = I.query(cand[i]);
                if (ans == 'Y') dup[i] = 1;
            }
        }

        for (size_t i = 0; i < cand.size(); i++) {
            if (!dup[i]) addRep(cand[i]);
        }
    }

    I.answer(d);
}