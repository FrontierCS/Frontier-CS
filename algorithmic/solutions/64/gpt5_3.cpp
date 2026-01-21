#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using u64 = unsigned long long;

static inline int64 absll(int64 x){ return x >= 0 ? x : -x; }

struct RNG {
    u64 s;
    RNG(): s(chrono::high_resolution_clock::now().time_since_epoch().count()) {}
    u64 next() {
        u64 z = (s += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    double nextDouble() { // in [0,1)
        return (next() >> 11) * (1.0/9007199254740992.0);
    }
    int nextInt(int n) { // [0, n)
        return (int)(next() % (u64)n);
    }
};

struct Node {
    int64 sum;
    int64 dist;
    u64 lo, hi; // selection bits in sorted order
};

static inline void set_bit(u64 &lo, u64 &hi, int k) {
    if (k < 64) lo |= (1ULL << k);
    else hi |= (1ULL << (k-64));
}
static inline bool get_bit(const u64 &lo, const u64 &hi, int k) {
    if (k < 64) return (lo >> k) & 1ULL;
    else return (hi >> (k-64)) & 1ULL;
}

vector<char> greedy_construct(const vector<int64>& a, int64 T, const vector<int>& order) {
    int n = (int)a.size();
    vector<char> x(n, '0');
    int64 sum = 0;
    for (int idx : order) {
        int64 ns = sum + a[idx];
        if (absll(T - ns) < absll(T - sum)) {
            x[idx] = '1';
            sum = ns;
        }
    }
    return x;
}

int64 compute_sum(const vector<int64>& a, const vector<char>& x){
    int n = (int)a.size();
    __int128 s = 0;
    for (int i = 0; i < n; ++i) if (x[i] == '1') s += a[i];
    return (int64)s;
}

void local_search(vector<char>& x, const vector<int64>& a, int64 T){
    int n = (int)a.size();
    int64 sum = compute_sum(a, x);
    int64 bestErr = absll(sum - T);

    // Single-flip steepest descent
    while (true) {
        int bestIdx = -1;
        int64 bestNewSum = sum;
        for (int i = 0; i < n; ++i) {
            int64 ns = x[i] == '1' ? sum - a[i] : sum + a[i];
            int64 e = absll(ns - T);
            if (e < bestErr) {
                bestErr = e;
                bestIdx = i;
                bestNewSum = ns;
            }
        }
        if (bestIdx == -1) break;
        x[bestIdx] = (x[bestIdx] == '1') ? '0' : '1';
        sum = bestNewSum;
    }

    // Pair-flip improvements
    while (true) {
        int64 curErr = absll(sum - T);
        int bi = -1, bj = -1;
        int64 bestNewSum = sum;

        // Prepare indices
        static int addIdx[128], remIdx[128];
        int na = 0, nr = 0;
        for (int i = 0; i < n; ++i) {
            if (x[i] == '1') remIdx[nr++] = i;
            else addIdx[na++] = i;
        }

        // add-remove
        for (int ii = 0; ii < na; ++ii) {
            int i = addIdx[ii];
            for (int jj = 0; jj < nr; ++jj) {
                int j = remIdx[jj];
                int64 ns = sum + a[i] - a[j];
                int64 e = absll(ns - T);
                if (e < curErr) {
                    curErr = e; bi = i; bj = j; bestNewSum = ns;
                }
            }
        }
        // add-add
        for (int ii = 0; ii < na; ++ii) {
            int i = addIdx[ii];
            for (int jj = ii+1; jj < na; ++jj) {
                int j = addIdx[jj];
                int64 ns = sum + a[i] + a[j];
                int64 e = absll(ns - T);
                if (e < curErr) {
                    curErr = e; bi = i; bj = j; bestNewSum = ns;
                }
            }
        }
        // rem-rem
        for (int ii = 0; ii < nr; ++ii) {
            int i = remIdx[ii];
            for (int jj = ii+1; jj < nr; ++jj) {
                int j = remIdx[jj];
                int64 ns = sum - a[i] - a[j];
                int64 e = absll(ns - T);
                if (e < curErr) {
                    curErr = e; bi = i; bj = j; bestNewSum = ns;
                }
            }
        }

        if (curErr < absll(sum - T)) {
            // Apply flips bi and bj
            if (bi != -1) x[bi] = (x[bi] == '1') ? '0' : '1';
            if (bj != -1) x[bj] = (x[bj] == '1') ? '0' : '1';
            sum = bestNewSum;
            // After a pair-step, do some single steps again
            while (true) {
                int bestIdx = -1;
                int64 bestNewSum2 = sum;
                int64 bestErr2 = absll(sum - T);
                for (int i = 0; i < n; ++i) {
                    int64 ns = x[i] == '1' ? sum - a[i] : sum + a[i];
                    int64 e = absll(ns - T);
                    if (e < bestErr2) {
                        bestErr2 = e;
                        bestIdx = i;
                        bestNewSum2 = ns;
                    }
                }
                if (bestIdx == -1) break;
                x[bestIdx] = (x[bestIdx] == '1') ? '0' : '1';
                sum = bestNewSum2;
            }
        } else break;
    }
}

vector<char> beam_search(const vector<int64>& a, int64 T, int beamWidth) {
    int n = (int)a.size();
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int i, int j){
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });

    vector<Node> curr;
    curr.reserve(beamWidth);
    curr.push_back(Node{0, absll(T), 0ULL, 0ULL});

    vector<Node> next;
    next.reserve(beamWidth*2);

    for (int k = 0; k < n; ++k) {
        int idx = ord[k];
        int64 val = a[idx];
        next.clear();
        next.reserve(min((int)curr.size()*2, beamWidth*2));

        for (const auto& c : curr) {
            // keep
            Node keep = c;
            keep.dist = absll(T - keep.sum);
            next.push_back(keep);
            // add
            Node addN = c;
            addN.sum = c.sum + val;
            if (k < 64) addN.lo |= (1ULL << k);
            else addN.hi |= (1ULL << (k - 64));
            addN.dist = absll(T - addN.sum);
            next.push_back(addN);
        }

        if ((int)next.size() > beamWidth) {
            nth_element(next.begin(), next.begin() + beamWidth, next.end(),
                        [](const Node& x, const Node& y){ return x.dist < y.dist; });
            next.resize(beamWidth);
        }
        curr.swap(next);
    }

    // pick best
    Node best = curr[0];
    for (const auto& c : curr) if (c.dist < best.dist) best = c;

    vector<char> res(n, '0');
    for (int k = 0; k < n; ++k) {
        int idx = ord[k];
        bool bit = get_bit(best.lo, best.hi, k);
        res[idx] = bit ? '1' : '0';
    }
    return res;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long T;
    if (!(cin >> n >> T)) {
        return 0;
    }
    vector<int64> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    // Edge cases
    int64 total = 0;
    for (int i = 0; i < n; ++i) total += a[i];
    if (T <= 0) {
        for (int i = 0; i < n; ++i) cout << '0';
        cout << '\n';
        return 0;
    }
    if (T >= total) {
        for (int i = 0; i < n; ++i) cout << '1';
        cout << '\n';
        return 0;
    }

    RNG rng;

    // Orders for greedy
    vector<int> ord_desc(n);
    iota(ord_desc.begin(), ord_desc.end(), 0);
    sort(ord_desc.begin(), ord_desc.end(), [&](int i, int j){
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });

    vector<int> ord_rand = ord_desc;
    shuffle(ord_rand.begin(), ord_rand.end(), std::mt19937_64(rng.next()));

    // Initial candidates
    vector<char> bestX(n, '0');
    int64 bestSum = 0;
    int64 bestErr = absll(T);

    auto try_update = [&](const vector<char>& x){
        int64 s = 0;
        for (int i = 0; i < n; ++i) if (x[i] == '1') s += a[i];
        int64 e = absll(s - T);
        if (e < bestErr) {
            bestErr = e; bestX = x; bestSum = s;
        }
    };

    // Greedy by desc
    auto g1 = greedy_construct(a, T, ord_desc);
    local_search(g1, a, T);
    try_update(g1);

    // Greedy by random order
    auto g2 = greedy_construct(a, T, ord_rand);
    local_search(g2, a, T);
    try_update(g2);

    // Beam search
    int beamW = 8192;
    auto b = beam_search(a, T, beamW);
    local_search(b, a, T);
    try_update(b);

    // Random restarts guided by p = T / total
    double p = (double)T / (double)total;
    if (p < 0.05) p = 0.05;
    if (p > 0.95) p = 0.95;

    // Budgeted small number of restarts
    int restarts = 20;
    for (int r = 0; r < restarts; ++r) {
        vector<char> xr(n, '0');
        int64 s = 0;
        for (int i = 0; i < n; ++i) {
            if (rng.nextDouble() < p) {
                xr[i] = '1';
                s += a[i];
            }
        }
        local_search(xr, a, T);
        try_update(xr);
        if (bestErr == 0) break; // exact match found
    }

    for (int i = 0; i < n; ++i) cout << bestX[i];
    cout << '\n';
    return 0;
}