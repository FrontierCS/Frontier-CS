#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto scoreErr = [&](long long sum)->unsigned long long{
        unsigned long long usum = (sum >= 0 ? (unsigned long long)sum : (unsigned long long)(-sum));
        unsigned long long uT = (T >= 0 ? (unsigned long long)T : (unsigned long long)(-T));
        if (sum >= T) return (unsigned long long)(sum - T);
        else return (unsigned long long)(T - sum);
    };

    vector<char> bestSel(n, 0);
    long long bestSum = 0;
    unsigned long long bestErr = scoreErr(0);

    auto greedy_build = [&](const vector<int>& order)->pair<vector<char>, long long>{
        vector<char> sel(n, 0);
        long long sum = 0;
        unsigned long long err = scoreErr(sum);
        for (int idx : order) {
            long long ns = sum + a[idx];
            unsigned long long ne = (ns >= T ? (unsigned long long)(ns - T) : (unsigned long long)(T - ns));
            if (ne < err) {
                sel[idx] = 1;
                sum = ns;
                err = ne;
            }
        }
        return {sel, sum};
    };

    auto one_opt = [&](vector<char>& sel, long long& sum){
        bool improved = true;
        while (improved) {
            improved = false;
            for (int i = 0; i < n; ++i) {
                long long ns = sel[i] ? (sum - a[i]) : (sum + a[i]);
                unsigned long long curErr = (sum >= T ? (unsigned long long)(sum - T) : (unsigned long long)(T - sum));
                unsigned long long newErr = (ns >= T ? (unsigned long long)(ns - T) : (unsigned long long)(T - ns));
                if (newErr < curErr) {
                    sel[i] ^= 1;
                    sum = ns;
                    improved = true;
                }
            }
        }
    };

    auto two_opt = [&](vector<char>& sel, long long& sum){
        while (true) {
            vector<pair<long long,int>> off;
            vector<int> on;
            off.reserve(n);
            on.reserve(n);
            for (int i = 0; i < n; ++i) {
                if (sel[i]) on.push_back(i);
                else off.emplace_back(a[i], i);
            }
            if (on.empty() || off.empty()) break;
            sort(off.begin(), off.end());
            vector<long long> offVals(off.size());
            for (size_t i = 0; i < off.size(); ++i) offVals[i] = off[i].first;
            long long R = T - sum;
            bool changed = false;
            unsigned long long curErr = (sum >= T ? (unsigned long long)(sum - T) : (unsigned long long)(T - sum));
            for (int iIdx : on) {
                long long target = R + a[iIdx]; // want add j (off) and remove i => change = -a[i] + a[j] ~ R => a[j] ~ R + a[i]
                auto it = lower_bound(offVals.begin(), offVals.end(), target);
                int bestj = -1;
                unsigned long long bestLocal = curErr;
                auto checkCandidate = [&](int pos){
                    if (pos < 0 || pos >= (int)off.size()) return;
                    int jIdx = off[pos].second;
                    long long ns = sum - a[iIdx] + a[jIdx];
                    unsigned long long ne = (ns >= T ? (unsigned long long)(ns - T) : (unsigned long long)(T - ns));
                    if (ne + 0ull < bestLocal) {
                        bestLocal = ne;
                        bestj = jIdx;
                    }
                };
                if (it != offVals.end()) checkCandidate((int)(it - offVals.begin()));
                if (it != offVals.begin()) checkCandidate((int)(it - offVals.begin()) - 1);
                if (bestj != -1) {
                    sel[iIdx] = 0;
                    sel[bestj] = 1;
                    sum = sum - a[iIdx] + a[bestj];
                    changed = true;
                    break;
                }
            }
            if (!changed) break;
            // optional: do one-opt after a successful two-opt step
            one_opt(sel, sum);
        }
    };

    auto attempt = [&](const vector<int>& order){
        auto [sel, sum] = greedy_build(order);
        one_opt(sel, sum);
        two_opt(sel, sum);
        unsigned long long err = scoreErr(sum);
        if (err < bestErr) {
            bestErr = err;
            bestSum = sum;
            bestSel = sel;
        }
    };

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    // Orderings
    vector<vector<int>> orders;

    // Descending by value
    {
        vector<int> o = idx;
        sort(o.begin(), o.end(), [&](int i, int j){ return a[i] > a[j]; });
        orders.push_back(o);
    }
    // Ascending by value
    {
        vector<int> o = idx;
        sort(o.begin(), o.end(), [&](int i, int j){ return a[i] < a[j]; });
        orders.push_back(o);
    }
    // By closeness to T/n
    {
        long double targetPer = (long double)T / max(1, n);
        vector<int> o = idx;
        sort(o.begin(), o.end(), [&](int i, int j){
            long double di = fabsl((long double)a[i] - targetPer);
            long double dj = fabsl((long double)a[j] - targetPer);
            if (di == dj) return a[i] > a[j];
            return di < dj;
        });
        orders.push_back(o);
    }
    // Random orders
    int random_trials = 6;
    for (int k = 0; k < random_trials; ++k) {
        vector<int> o = idx;
        shuffle(o.begin(), o.end(), rng);
        orders.push_back(o);
    }

    auto startTime = chrono::high_resolution_clock::now();
    const double timeLimit = 0.9; // seconds
    int round = 0;

    while (true) {
        for (auto& o : orders) {
            attempt(o);
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - startTime).count();
            if (elapsed > timeLimit) goto done;
        }
        // additional random attempts
        vector<int> o = idx;
        shuffle(o.begin(), o.end(), rng);
        attempt(o);
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > timeLimit) break;
        round++;
        if (round > 50) break;
    }

done:
    for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
    cout << '\n';
    return 0;
}