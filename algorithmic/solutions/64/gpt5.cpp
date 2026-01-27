#include <bits/stdc++.h>
using namespace std;

static inline unsigned long long absDiff(long long a, long long b) {
    return (a >= b) ? (unsigned long long)(a - b) : (unsigned long long)(b - a);
}

struct Node {
    long long sum;
    int prev;
    uint8_t take;
};

struct Cand {
    long long sum;
    int prev;
    uint8_t take;
};

pair<vector<char>, long long> beam_search(const vector<long long>& a, const vector<int>& ord, long long T, int Lmax) {
    int n = (int)ord.size();
    vector<vector<Node>> layers;
    layers.reserve(n + 1);
    layers.push_back(vector<Node>(1));
    layers[0][0] = {0LL, -1, 0};

    vector<Cand> cand;
    cand.reserve(Lmax * 2 + 10);

    for (int i = 0; i < n; ++i) {
        const auto& prev = layers.back();
        int m = (int)prev.size();
        cand.clear();
        cand.resize(m * 2);
        long long w = a[ord[i]];

        for (int j = 0; j < m; ++j) {
            cand[2*j] = { prev[j].sum, j, 0 };
            cand[2*j + 1] = { prev[j].sum + w, j, 1 };
        }

        auto cmp = [&](const Cand& x, const Cand& y) {
            auto dx = absDiff(x.sum, T);
            auto dy = absDiff(y.sum, T);
            if (dx != dy) return dx < dy;
            return x.sum < y.sum;
        };

        int keep = min((int)cand.size(), Lmax);
        if ((int)cand.size() > keep) {
            nth_element(cand.begin(), cand.begin() + keep, cand.end(), cmp);
            cand.resize(keep);
        }

        // Optional small sort to stabilize (not necessary but can help determinism)
        sort(cand.begin(), cand.end(), cmp);

        vector<Node> cur;
        cur.reserve(cand.size());
        for (auto &c : cand) {
            cur.push_back({c.sum, c.prev, c.take});
        }

        layers.push_back(move(cur));
    }

    // Find best in final layer
    const auto& last = layers.back();
    int best_idx = 0;
    unsigned long long best_err = ULLONG_MAX;
    for (int i = 0; i < (int)last.size(); ++i) {
        auto e = absDiff(last[i].sum, T);
        if (e < best_err) {
            best_err = e;
            best_idx = i;
        }
    }

    vector<char> pick(a.size(), 0);
    int idx = best_idx;
    for (int i = n; i >= 1; --i) {
        const Node &cur = layers[i][idx];
        if (cur.take) pick[ord[i-1]] = 1;
        idx = cur.prev;
    }

    return {pick, last[best_idx].sum};
}

pair<vector<char>, long long> greedy_pass(const vector<long long>& a, const vector<int>& ord, long long T) {
    vector<char> pick(a.size(), 0);
    long long s = 0;
    for (int id : ord) {
        if (absDiff(s + a[id], T) <= absDiff(s, T)) {
            s += a[id];
            pick[id] = 1;
        }
    }
    return {pick, s};
}

void improve_single_flip(vector<char>& pick, long long& sum, const vector<long long>& a, long long T) {
    bool improved = true;
    int n = (int)a.size();
    while (improved) {
        improved = false;
        unsigned long long curErr = absDiff(sum, T);
        for (int i = 0; i < n; ++i) {
            long long ns = pick[i] ? sum - a[i] : sum + a[i];
            auto ne = absDiff(ns, T);
            if (ne < curErr) {
                pick[i] = !pick[i];
                sum = ns;
                curErr = ne;
                improved = true;
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    auto start = chrono::steady_clock::now();
    const double timeLimitSec = 1.8;

    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);

    // Determine beam width based on n
    int Lmax;
    if (n <= 30) Lmax = 40000;
    else if (n <= 50) Lmax = 20000;
    else if (n <= 70) Lmax = 12000;
    else if (n <= 85) Lmax = 9000;
    else Lmax = 7000;

    // Candidates orders
    vector<vector<int>> orders;

    // Descending by value
    {
        vector<int> o = ord;
        sort(o.begin(), o.end(), [&](int i, int j){ return a[i] > a[j]; });
        orders.push_back(move(o));
    }
    // Ascending by value
    {
        vector<int> o = ord;
        sort(o.begin(), o.end(), [&](int i, int j){ return a[i] < a[j]; });
        orders.push_back(move(o));
    }
    // Original
    orders.push_back(ord);

    // Alternate large-small
    {
        vector<int> o = ord;
        sort(o.begin(), o.end(), [&](int i, int j){ return a[i] > a[j]; });
        vector<int> alt;
        alt.reserve(n);
        int l = 0, r = n - 1;
        while (l <= r) {
            alt.push_back(o[l++]);
            if (l <= r) alt.push_back(o[r--]);
        }
        orders.push_back(move(alt));
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    // Add a few random shuffles
    for (int k = 0; k < 6; ++k) {
        vector<int> o = ord;
        shuffle(o.begin(), o.end(), rng);
        orders.push_back(move(o));
    }

    vector<char> bestPick(n, 0);
    long long bestSum = 0;
    unsigned long long bestErr = ULLONG_MAX;

    auto keep_best = [&](const vector<char>& pick, long long sum) {
        auto err = absDiff(sum, T);
        if (err < bestErr) {
            bestErr = err;
            bestPick = pick;
            bestSum = sum;
        }
    };

    // Try greedy orders quickly
    for (auto &o : orders) {
        auto g = greedy_pass(a, o, T);
        keep_best(g.first, g.second);
        if (bestErr == 0) break;
        auto now = chrono::steady_clock::now();
        if (chrono::duration<double>(now - start).count() > timeLimitSec) break;
    }

    // Beam search on various orders until time runs out or exact match
    for (auto &o : orders) {
        auto now = chrono::steady_clock::now();
        if (chrono::duration<double>(now - start).count() > timeLimitSec) break;

        auto res = beam_search(a, o, T, Lmax);
        improve_single_flip(res.first, res.second, a, T);
        keep_best(res.first, res.second);
        if (bestErr == 0) break;
    }

    // Final minor random local search if time allows
    {
        auto now = chrono::steady_clock::now();
        double remain = timeLimitSec - chrono::duration<double>(now - start).count();
        if (remain > 0.05) {
            vector<char> cur = bestPick;
            long long sum = bestSum;
            int trials = 1000;
            int nrand = (int)min<long long>(trials, (long long)remain * 20000);
            uniform_int_distribution<int> dist(0, max(0, n - 1));
            for (int t = 0; t < nrand; ++t) {
                int i = dist(rng);
                int j = dist(rng);
                if (i == j) continue;
                long long ns = sum + (cur[i] ? -a[i] : a[i]) + (cur[j] ? -a[j] : a[j]);
                if (absDiff(ns, T) < absDiff(sum, T)) {
                    cur[i] = !cur[i];
                    cur[j] = !cur[j];
                    sum = ns;
                }
            }
            improve_single_flip(cur, sum, a, T);
            if (absDiff(sum, T) < bestErr) {
                bestErr = absDiff(sum, T);
                bestPick = move(cur);
                bestSum = sum;
            }
        }
    }

    string out;
    out.resize(n);
    for (int i = 0; i < n; ++i) out[i] = bestPick[i] ? '1' : '0';
    cout << out << '\n';
    return 0;
}