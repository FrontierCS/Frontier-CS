#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool read(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar())
            val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
};

int N, M;
int B; // number of 64-bit blocks
ull LAST_MASK; // mask for last block
vector<vector<ull>> adj; // adjacency bitsets
vector<int> degv;
vector<ull> FULLONES;

mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
chrono::steady_clock::time_point DEADLINE;

inline bool time_up() {
    return chrono::steady_clock::now() >= DEADLINE;
}

inline int popcount_bs(const vector<ull>& bs) {
    int s = 0;
    for (int i = 0; i < (int)bs.size(); ++i) s += __builtin_popcountll(bs[i]);
    return s;
}

inline int popcount_intersection_v_cand(int v, const vector<ull>& cand) {
    int s = 0;
    const vector<ull>& av = adj[v];
    for (int i = 0; i < B; ++i) s += __builtin_popcountll(av[i] & cand[i]);
    return s;
}

inline void and_with(vector<ull>& a, const vector<ull>& b) {
    for (int i = 0; i < B; ++i) a[i] &= b[i];
}

inline void and_with_mask(vector<ull>& a, const vector<ull>& b) {
    for (int i = 0; i < B; ++i) a[i] &= b[i];
    if (B) a[B-1] &= LAST_MASK;
}

inline bool is_zero_bs(const vector<ull>& bs) {
    for (int i = 0; i < B; ++i) if (bs[i]) return false;
    return true;
}

inline void set_bit(vector<ull>& bs, int idx) {
    bs[idx >> 6] |= (1ULL << (idx & 63));
}

inline void clear_bit(vector<ull>& bs, int idx) {
    bs[idx >> 6] &= ~(1ULL << (idx & 63));
}

inline bool test_bit(const vector<ull>& bs, int idx) {
    return (bs[idx >> 6] >> (idx & 63)) & 1ULL;
}

inline vector<int> enumerate_set_bits(const vector<ull>& bs) {
    vector<int> res;
    res.reserve(64);
    for (int i = 0; i < B; ++i) {
        ull w = bs[i];
        while (w) {
            int t = __builtin_ctzll(w);
            int idx = (i << 6) + t;
            if (idx < N) res.push_back(idx);
            w &= w - 1;
        }
    }
    return res;
}

inline int first_set_bit(const vector<ull>& bs) {
    for (int i = 0; i < B; ++i) {
        ull w = bs[i];
        if (w) {
            int t = __builtin_ctzll(w);
            int idx = (i << 6) + t;
            if (idx < N) return idx;
        }
    }
    return -1;
}

vector<int> greedy_from_clique(const vector<int>& initial, bool randomize) {
    vector<ull> cand = FULLONES;
    for (int u : initial) and_with_mask(cand, adj[u]);
    vector<int> clique = initial;
    while (!is_zero_bs(cand)) {
        if (time_up()) break;
        vector<int> cand_idx = enumerate_set_bits(cand);
        if (cand_idx.empty()) break;
        int max_sc = -1, min_sc = INT_MAX;
        vector<int> scores;
        scores.reserve(cand_idx.size());
        for (int u : cand_idx) {
            int sc = popcount_intersection_v_cand(u, cand);
            scores.push_back(sc);
            if (sc > max_sc) max_sc = sc;
            if (sc < min_sc) min_sc = sc;
        }
        int threshold = max_sc;
        if (randomize) threshold = max(0, max_sc - 1);
        vector<int> rcl;
        rcl.reserve(32);
        for (size_t i = 0; i < cand_idx.size(); ++i) {
            if (scores[i] >= threshold) rcl.push_back(cand_idx[i]);
        }
        int v;
        if (rcl.empty()) {
            // fallback to max-scored
            int best_v = cand_idx[0];
            int best_s = scores[0];
            for (size_t i = 1; i < cand_idx.size(); ++i) {
                if (scores[i] > best_s || (scores[i] == best_s && degv[cand_idx[i]] > degv[best_v])) {
                    best_s = scores[i]; best_v = cand_idx[i];
                }
            }
            v = best_v;
        } else {
            v = rcl[rng() % rcl.size()];
        }
        clique.push_back(v);
        and_with_mask(cand, adj[v]);
    }
    return clique;
}

vector<int> greedy_from_start(int s, bool randomize) {
    vector<int> init{ s };
    return greedy_from_clique(init, randomize);
}

vector<int> greedy_from_pair(int a, int b, bool randomize) {
    if (a == b) return greedy_from_start(a, randomize);
    // ensure edge
    if (!test_bit(adj[a], b)) return greedy_from_start(a, randomize);
    vector<int> init{ a, b };
    return greedy_from_clique(init, randomize);
}

void build_fullones() {
    FULLONES.assign(B, ~0ULL);
    if (B) FULLONES[B - 1] &= LAST_MASK;
}

vector<int> local_search_swap_improve(vector<int> best_clique) {
    // Build bitset and inC flags
    vector<ull> C(B, 0);
    vector<char> inC(N, 0);
    for (int u : best_clique) {
        set_bit(C, u);
        inC[u] = 1;
    }
    int k = (int)best_clique.size();

    auto rebuild_from = [&](const vector<int>& clq_list) {
        vector<ull> bs(B, 0);
        vector<char> mark(N, 0);
        for (int u : clq_list) { set_bit(bs, u); mark[u] = 1; }
        return pair<vector<ull>, vector<char>>(bs, mark);
    };

    bool improved = true;
    int attempts = 0;
    while (improved && !time_up()) {
        improved = false;
        // Try 1-swap improvements
        for (int w = 0; w < N && !improved && !time_up(); ++w) {
            if (inC[w]) continue;
            int common = 0;
            for (int i = 0; i < B; ++i) common += __builtin_popcountll(adj[w][i] & C[i]);
            int missing = k - common;
            if (missing == 1) {
                // find the single r in C not adjacent to w
                vector<ull> missed(B, 0);
                for (int i = 0; i < B; ++i) missed[i] = C[i] & ~adj[w][i];
                if (B) missed[B-1] &= LAST_MASK;
                int r = first_set_bit(missed);
                if (r == -1) continue;
                // Build new clique list: replace r by w
                vector<int> new_list = best_clique;
                for (int &x : new_list) if (x == r) { x = w; break; }
                // Expand greedily without randomness
                vector<int> expanded = greedy_from_clique(new_list, false);
                if ((int)expanded.size() > k) {
                    // Accept improvement
                    best_clique.swap(expanded);
                    auto rebuilt = rebuild_from(best_clique);
                    C.swap(rebuilt.first);
                    inC.swap(rebuilt.second);
                    k = (int)best_clique.size();
                    improved = true;
                }
            }
        }
        attempts++;
        if (attempts > 10) break; // limit iterations
    }
    return best_clique;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    if (!fs.read(N)) return 0;
    fs.read(M);

    B = (N + 63) >> 6;
    int rem = N & 63;
    LAST_MASK = (rem == 0) ? ~0ULL : ((1ULL << rem) - 1ULL);

    adj.assign(N, vector<ull>(B, 0ULL));

    for (int i = 0; i < M; ++i) {
        int u, v;
        fs.read(u); fs.read(v);
        --u; --v;
        if (u == v || u < 0 || v < 0 || u >= N || v >= N) continue;
        adj[u][v >> 6] |= (1ULL << (v & 63));
        adj[v][u >> 6] |= (1ULL << (u & 63));
    }

    build_fullones();

    degv.assign(N, 0);
    for (int i = 0; i < N; ++i) {
        int d = 0;
        for (int b = 0; b < B; ++b) d += __builtin_popcountll(adj[i][b]);
        degv[i] = d;
    }

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (degv[a] != degv[b]) return degv[a] > degv[b];
        return a < b;
    });

    DEADLINE = chrono::steady_clock::now() + chrono::milliseconds(1900);

    vector<int> best_clique;
    int best_size = 0;

    auto update_best = [&](const vector<int>& clq) {
        if ((int)clq.size() > best_size) {
            best_size = (int)clq.size();
            best_clique = clq;
        }
    };

    int Kstart = min(N, 30);
    for (int i = 0; i < Kstart && !time_up(); ++i) {
        int s = order[i];
        // Single start
        auto clq1 = greedy_from_start(s, false);
        update_best(clq1);
        if (time_up()) break;
        // Pair start with best neighbor
        vector<ull> neigh = adj[s];
        if (!is_zero_bs(neigh)) {
            vector<int> neigh_list = enumerate_set_bits(neigh);
            int best_v = -1, best_score = -1;
            for (int v : neigh_list) {
                int sc = 0;
                for (int b = 0; b < B; ++b) sc += __builtin_popcountll(adj[v][b] & neigh[b]);
                if (sc > best_score || (sc == best_score && degv[v] > (best_v == -1 ? -1 : degv[best_v]))) {
                    best_score = sc; best_v = v;
                }
                if (time_up()) break;
            }
            if (!time_up() && best_v != -1) {
                auto clq2 = greedy_from_pair(s, best_v, false);
                update_best(clq2);
            }
        }
    }

    // Random restarts
    while (!time_up()) {
        int s = rng() % N;
        auto clq = greedy_from_start(s, true);
        update_best(clq);
    }

    // Local search improvement
    if (!time_up() && !best_clique.empty()) {
        best_clique = local_search_swap_improve(best_clique);
        best_size = (int)best_clique.size();
    }

    vector<char> in_best(N, 0);
    for (int u : best_clique) in_best[u] = 1;

    for (int i = 0; i < N; ++i) {
        cout << (in_best[i] ? 1 : 0) << '\n';
    }

    return 0;
}