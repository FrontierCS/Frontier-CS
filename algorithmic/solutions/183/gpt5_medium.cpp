#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getc_() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template <typename T>
    bool readInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getc_();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getc_();
            if (c == EOF) return false;
        }
        if (c == '-') {
            sign = -1;
            c = getc_();
        }
        for (; c >= '0' && c <= '9'; c = getc_()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    vector<vector<int>> G(N + 1);
    G.reserve(N + 1);

    int u, v;
    for (int i = 0; i < M; ++i) {
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue;
        G[u].push_back(v);
        G[v].push_back(u);
    }

    vector<int> deg(N + 1);
    for (int i = 1; i <= N; ++i) deg[i] = (int)G[i].size();

    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t(new int));
    mt19937_64 rng(seed);

    auto start = chrono::steady_clock::now();
    auto time_elapsed_ms = [&]() -> double {
        return chrono::duration<double, milli>(chrono::steady_clock::now() - start).count();
    };
    const double TIME_LIMIT_MS = 1800.0;

    vector<char> best_sel(N + 1, 0);
    int best_K = 0;

    // Heuristic A: Dynamic min-degree greedy
    {
        vector<int> cur_deg = deg;
        vector<char> alive(N + 1, 1), sel(N + 1, 0);
        vector<uint32_t> tiekey(N + 1);
        for (int i = 1; i <= N; ++i) tiekey[i] = (uint32_t)rng();

        using Node = pair<pair<int, uint32_t>, int>; // ((deg, tie), node)
        priority_queue<Node, vector<Node>, greater<Node>> pq;
        for (int i = 1; i <= N; ++i) pq.push({{cur_deg[i], tiekey[i]}, i});

        int alive_cnt = N;

        auto remove_vertex = [&](int x) {
            if (!alive[x]) return;
            alive[x] = 0;
            --alive_cnt;
        };

        auto decrease_deg_of_neighbors = [&](int x) {
            for (int y : G[x]) {
                if (alive[y]) {
                    --cur_deg[y];
                    pq.push({{cur_deg[y], tiekey[y]}, y});
                }
            }
        };

        while (alive_cnt > 0) {
            if (pq.empty()) break;
            auto top = pq.top(); pq.pop();
            int d = top.first.first;
            int x = top.second;
            if (!alive[x]) continue;
            if (cur_deg[x] != d) continue;

            // Select x
            sel[x] = 1;
            // Remove x
            remove_vertex(x);

            // Remove neighbors and update degrees of their neighbors
            for (int nb : G[x]) {
                if (alive[nb]) {
                    remove_vertex(nb);
                    decrease_deg_of_neighbors(nb);
                }
            }
        }

        int K = 0;
        for (int i = 1; i <= N; ++i) K += sel[i];
        best_sel = move(sel);
        best_K = K;
    }

    // Heuristic B: Multiple randomized greedy trials (sequential)
    vector<int> order(N);
    iota(order.begin(), order.end(), 1);

    auto eval_order = [&](const vector<int>& ord, vector<char>& out_sel) -> int {
        vector<char> banned(N + 1, 0);
        out_sel.assign(N + 1, 0);
        int K = 0;
        for (int vtx : ord) {
            if (!banned[vtx]) {
                out_sel[vtx] = 1;
                ++K;
                banned[vtx] = 1;
                for (int nb : G[vtx]) banned[nb] = 1;
            }
        }
        return K;
    };

    // One degree-ascending trial with random tie-break
    if (time_elapsed_ms() < TIME_LIMIT_MS) {
        vector<pair<int, int>> deg_idx(N);
        for (int i = 1; i <= N; ++i) deg_idx[i - 1] = {deg[i], i};
        // randomize tie-breaking
        shuffle(deg_idx.begin(), deg_idx.end(), rng);
        stable_sort(deg_idx.begin(), deg_idx.end(), [](const pair<int,int>& a, const pair<int,int>& b){
            if (a.first != b.first) return a.first < b.first;
            return a.second < b.second;
        });
        for (int i = 0; i < N; ++i) order[i] = deg_idx[i].second;

        vector<char> sel(N + 1, 0);
        int K = eval_order(order, sel);
        if (K > best_K) {
            best_K = K;
            best_sel = move(sel);
        }
    }

    // Random shuffles until time runs out
    while (time_elapsed_ms() < TIME_LIMIT_MS) {
        shuffle(order.begin(), order.end(), rng);
        vector<char> sel(N + 1, 0);
        int K = eval_order(order, sel);
        if (K > best_K) {
            best_K = K;
            best_sel = move(sel);
        }
    }

    // Output
    // Optional validation (disabled in final to save time)
    // for (int i = 1; i <= N; ++i) for (int j : G[i]) if (i < j && best_sel[i] && best_sel[j]) {/*invalid*/}

    string out;
    out.reserve(N * 2);
    for (int i = 1; i <= N; ++i) {
        out += (best_sel[i] ? '1' : '0');
        out += '\n';
    }
    cout << out;
    return 0;
}