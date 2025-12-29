#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct Plan {
    array<int, 100> a{};
    array<int, 100> b{};
    long long err = (1LL << 60);
    array<int, 100> cnt{};
};

static inline long long simulate_plan(const array<int, 100>& a, const array<int, 100>& b,
                                      const array<int, 100>& T, int L,
                                      array<int, 100>& cnt_out) {
    cnt_out.fill(0);
    int cur = 0;
    for (int step = 0; step < L; step++) {
        int& cc = cnt_out[cur];
        cc++;
        if (step + 1 == L) break;
        cur = (cc & 1) ? a[cur] : b[cur];
    }
    long long err = 0;
    for (int i = 0; i < 100; i++) err += llabs((long long)cnt_out[i] - (long long)T[i]);
    return err;
}

static inline vector<int> make_order_desc(const array<int, 100>& T) {
    vector<int> ord(100);
    iota(ord.begin(), ord.end(), 0);
    stable_sort(ord.begin(), ord.end(), [&](int x, int y) {
        if (T[x] != T[y]) return T[x] > T[y];
        return x < y;
    });
    return ord;
}

static inline vector<int> make_order_asc(const array<int, 100>& T) {
    vector<int> ord(100);
    iota(ord.begin(), ord.end(), 0);
    stable_sort(ord.begin(), ord.end(), [&](int x, int y) {
        if (T[x] != T[y]) return T[x] < T[y];
        return x < y;
    });
    return ord;
}

static inline Plan build_candidate(const vector<int>& order, const array<int, 100>& T, uint64_t& seed) {
    Plan p;
    // a: cycle by given order
    for (int k = 0; k < 100; k++) {
        int u = order[k];
        int v = order[(k + 1) % 100];
        p.a[u] = v;
    }

    // R[j] = 2*T[j] - sum_{i: a[i]==j} T[i]
    array<long long, 100> inA{};
    inA.fill(0);
    for (int i = 0; i < 100; i++) inA[p.a[i]] += T[i];

    array<long long, 100> D{};
    for (int j = 0; j < 100; j++) D[j] = 2LL * T[j] - inA[j];

    vector<int> srcs(100);
    iota(srcs.begin(), srcs.end(), 0);
    stable_sort(srcs.begin(), srcs.end(), [&](int x, int y) {
        if (T[x] != T[y]) return T[x] > T[y];
        return x < y;
    });

    for (int i : srcs) {
        long long mx = D[0];
        for (int j = 1; j < 100; j++) mx = max(mx, D[j]);
        int best = -1;
        int ties = 0;
        for (int j = 0; j < 100; j++) {
            if (D[j] == mx) {
                ties++;
                uint64_t r = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
                if ((int)(r % ties) == 0) best = j;
            }
        }
        if (best < 0) best = 0;
        p.b[i] = best;
        D[best] -= T[i];
    }

    return p;
}

static inline int pick_weighted_deficit(const array<int, 100>& deficit, uint64_t& seed) {
    long long sum = 0;
    for (int i = 0; i < 100; i++) sum += max(0, deficit[i]);
    if (sum <= 0) {
        uint64_t r = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
        return (int)(r % 100);
    }
    uint64_t r = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
    long long x = (long long)(r % (uint64_t)sum);
    for (int i = 0; i < 100; i++) {
        long long w = max(0, deficit[i]);
        if (x < w) return i;
        x -= w;
    }
    return 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, L;
    cin >> N >> L;
    array<int, 100> T{};
    for (int i = 0; i < N; i++) cin >> T[i];

    uint64_t seed = 123456789ULL;
    seed ^= (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();

    vector<vector<int>> orders;
    orders.push_back(make_order_desc(T));
    orders.push_back(make_order_asc(T));
    {
        vector<int> rnd(100);
        iota(rnd.begin(), rnd.end(), 0);
        for (int i = 99; i >= 1; i--) {
            uint64_t r = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
            int j = (int)(r % (uint64_t)(i + 1));
            swap(rnd[i], rnd[j]);
        }
        orders.push_back(rnd);
    }
    {
        // Slightly perturbed descending
        auto ord = make_order_desc(T);
        for (int t = 0; t < 40; t++) {
            uint64_t r1 = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
            uint64_t r2 = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
            int i = (int)(r1 % 100);
            int j = (int)(r2 % 100);
            swap(ord[i], ord[j]);
        }
        orders.push_back(ord);
    }

    Plan best;
    best.err = (1LL << 60);

    // Evaluate candidates
    for (auto& ord : orders) {
        uint64_t local_seed = seed;
        Plan p = build_candidate(ord, T, local_seed);
        p.err = simulate_plan(p.a, p.b, T, L, p.cnt);
        if (p.err < best.err) best = p;
    }

    // Local search on b only
    Plan cur = best;
    array<int, 100> deficit{};
    auto update_deficit = [&]() {
        for (int i = 0; i < 100; i++) deficit[i] = T[i] - cur.cnt[i];
    };
    update_deficit();

    const double TL = 1.85;
    auto t_start = chrono::steady_clock::now();

    const double temp_start = 6000.0;
    const double temp_end = 50.0;

    int iters = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double t = chrono::duration<double>(now - t_start).count();
        if (t >= TL) break;
        double frac = t / TL;
        double temp = temp_start * pow(temp_end / temp_start, frac);

        uint64_t r1 = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
        int i = (int)(r1 % 100);

        int new_to = pick_weighted_deficit(deficit, seed);
        if (new_to == cur.b[i]) {
            uint64_t r2 = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
            new_to = (int)(r2 % 100);
        }

        int old_to = cur.b[i];
        cur.b[i] = new_to;

        array<int, 100> cnt2{};
        long long err2 = simulate_plan(cur.a, cur.b, T, L, cnt2);
        long long delta = err2 - cur.err;

        bool accept = false;
        if (delta <= 0) {
            accept = true;
        } else {
            double prob = exp(- (double)delta / temp);
            uint64_t r3 = splitmix64(seed += 0x9e3779b97f4a7c15ULL);
            double u = (double)((r3 >> 11) * (1.0 / 9007199254740992.0)); // [0,1)
            accept = (u < prob);
        }

        if (accept) {
            cur.err = err2;
            cur.cnt = cnt2;
            update_deficit();
            if (cur.err < best.err) best = cur;
        } else {
            cur.b[i] = old_to;
        }

        iters++;
        if ((iters & 31) == 0) {
            // occasionally intensify towards deficits by making small directed tweaks
            // (kept cheap: no extra sim here)
        }
    }

    for (int i = 0; i < N; i++) {
        cout << best.a[i] << ' ' << best.b[i] << "\n";
    }
    return 0;
}