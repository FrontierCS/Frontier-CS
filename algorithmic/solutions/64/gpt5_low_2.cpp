#include <bits/stdc++.h>
using namespace std;

using i64 = long long;
using u64 = unsigned long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    auto now = [](){ return chrono::high_resolution_clock::now(); };
    auto start = now();
    auto elapsed_ms = [&](double ms){
        return chrono::duration<double, std::milli>(now() - start).count() >= ms;
    };
    const double TIME_LIMIT_MS = 950.0;

    // Random engine
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    // Helper: compute error
    auto err = [&](long long sum)->unsigned __int128 {
        long long diff = sum - T;
        if (diff < 0) diff = -diff;
        return (unsigned __int128)diff;
    };

    // Greedy constructor along an order
    auto greedy_build = [&](const vector<int>& order){
        vector<char> sel(n, 0);
        long long sum = 0;
        for (int idx : order) {
            long long ns = sum + a[idx];
            long long d1 = llabs(ns - T);
            long long d0 = llabs(sum - T);
            if (d1 <= d0) {
                sel[idx] = 1;
                sum = ns;
            }
        }
        return pair<vector<char>, long long>(sel, sum);
    };

    // Compute error for selection
    auto compute_sum = [&](const vector<char>& sel){
        __int128 s = 0;
        for (int i = 0; i < n; ++i) if (sel[i]) s += a[i];
        long long sum = (long long)s;
        return sum;
    };

    // Single-flip hill climbing
    auto single_flip_improve = [&](vector<char>& sel, long long& sum)->bool{
        unsigned __int128 bestErr = err(sum);
        int bestIdx = -1;
        long long bestNewSum = sum;
        long long d = T - sum;
        for (int i = 0; i < n; ++i) {
            long long delta = sel[i] ? -a[i] : a[i];
            long long ns = sum + delta;
            unsigned __int128 ne = err(ns);
            if (ne < bestErr) {
                bestErr = ne;
                bestIdx = i;
                bestNewSum = ns;
            }
        }
        if (bestIdx != -1) {
            sel[bestIdx] ^= 1;
            sum = bestNewSum;
            return true;
        }
        return false;
    };

    // Two-flip improvement via two-pointer on deltas
    auto two_flip_improve = [&](vector<char>& sel, long long& sum)->bool{
        unsigned __int128 curErr = err(sum);
        long long d = T - sum;
        vector<pair<long long,int>> deltas;
        deltas.reserve(n);
        for (int i = 0; i < n; ++i) {
            long long delta = sel[i] ? -a[i] : a[i];
            deltas.emplace_back(delta, i);
        }
        sort(deltas.begin(), deltas.end(), [](const auto& x, const auto& y){
            if (x.first != y.first) return x.first < y.first;
            return x.second < y.second;
        });
        int l = 0, r = (int)deltas.size() - 1;
        unsigned __int128 bestErr = curErr;
        int bi = -1, bj = -1;
        long long bestSum = sum;
        while (l < r) {
            long long s2 = deltas[l].first + deltas[r].first;
            long long ns = sum + s2;
            unsigned __int128 ne = err(ns);
            if (ne < bestErr) {
                bestErr = ne;
                bi = deltas[l].second;
                bj = deltas[r].second;
                bestSum = ns;
            }
            if (s2 < d) ++l;
            else if (s2 > d) --r;
            else break; // perfect match
        }
        if (bi != -1 && bj != -1 && bi != bj && bestErr < curErr) {
            sel[bi] ^= 1;
            sel[bj] ^= 1;
            sum = bestSum;
            return true;
        }
        return false;
    };

    // Initialize with several greedy attempts
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    vector<char> bestSel(n, 0);
    long long bestSum = 0;
    unsigned __int128 bestErr = err(0);

    // Orders to try: original, ascending, descending, random shuffles
    {
        // Original
        auto p = greedy_build(idx);
        if (err(p.second) < bestErr) { bestErr = err(p.second); bestSel = p.first; bestSum = p.second; }
        if (elapsed_ms(TIME_LIMIT_MS)) {
            // Output and exit
            for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
            cout << '\n';
            return 0;
        }

        // Ascending by a
        vector<int> ord = idx;
        sort(ord.begin(), ord.end(), [&](int i, int j){ return a[i] < a[j]; });
        p = greedy_build(ord);
        if (err(p.second) < bestErr) { bestErr = err(p.second); bestSel = p.first; bestSum = p.second; }
        if (elapsed_ms(TIME_LIMIT_MS)) {
            for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
            cout << '\n';
            return 0;
        }

        // Descending by a
        sort(ord.begin(), ord.end(), [&](int i, int j){ return a[i] > a[j]; });
        p = greedy_build(ord);
        if (err(p.second) < bestErr) { bestErr = err(p.second); bestSel = p.first; bestSum = p.second; }
        if (elapsed_ms(TIME_LIMIT_MS)) {
            for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
            cout << '\n';
            return 0;
        }

        // By closeness to T/n
        long double avg = (long double)T / max(1, n);
        ord = idx;
        sort(ord.begin(), ord.end(), [&](int i, int j){
            long double di = fabsl((long double)a[i] - avg);
            long double dj = fabsl((long double)a[j] - avg);
            if (di != dj) return di < dj;
            return i < j;
        });
        p = greedy_build(ord);
        if (err(p.second) < bestErr) { bestErr = err(p.second); bestSel = p.first; bestSum = p.second; }
        if (elapsed_ms(TIME_LIMIT_MS)) {
            for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
            cout << '\n';
            return 0;
        }

        // Several random shuffles
        int attempts = 200;
        for (int it = 0; it < attempts; ++it) {
            shuffle(ord.begin(), ord.end(), rng);
            auto pp = greedy_build(ord);
            unsigned __int128 e = err(pp.second);
            if (e < bestErr) {
                bestErr = e; bestSel = pp.first; bestSum = pp.second;
            }
            if (elapsed_ms(TIME_LIMIT_MS * 0.45)) break;
        }
    }

    // Local search: single and two-flip improvements
    while (!elapsed_ms(TIME_LIMIT_MS)) {
        bool improved = false;
        // Try single flips until no improvement
        while (!elapsed_ms(TIME_LIMIT_MS)) {
            if (!single_flip_improve(bestSel, bestSum)) break;
            improved = true;
        }
        if (elapsed_ms(TIME_LIMIT_MS)) break;
        // Try two-flip improvement
        if (two_flip_improve(bestSel, bestSum)) {
            improved = true;
        }
        if (!improved) {
            // Small random perturbation to escape local minima
            uniform_int_distribution<int> dist(0, n-1);
            int flips = 1 + (rng() % 2); // flip 1 or 2 bits
            for (int k = 0; k < flips; ++k) {
                int i = dist(rng);
                bestSel[i] ^= 1;
                bestSum += bestSel[i] ? a[i] : -a[i];
            }
            // Immediately hill-climb a bit
            for (int iter = 0; iter < 3; ++iter) {
                if (!single_flip_improve(bestSel, bestSum)) break;
                if (elapsed_ms(TIME_LIMIT_MS)) break;
            }
        }
    }

    // Output selection as binary string
    for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
    cout << '\n';
    return 0;
}