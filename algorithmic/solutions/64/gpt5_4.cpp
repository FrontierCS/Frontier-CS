#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct PairEntry {
    ll sum;
    int i, j; // original indices
    bool operator<(const PairEntry& other) const { return sum < other.sum; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    ll T;
    if(!(cin >> n >> T)) {
        return 0;
    }
    vector<ll> a(n);
    for(int i=0;i<n;i++) cin >> a[i];

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.9;

    auto time_exceeded = [&](){
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        return elapsed > TIME_LIMIT_SEC;
    };

    ll sumAll = 0;
    for (ll v : a) sumAll += v;
    if (sumAll == 0) {
        string s(n, '0');
        cout << s;
        return 0;
    }

    // Helper to compute sum from bits
    auto compute_sum = [&](const vector<char>& bits)->ll{
        ll s=0;
        for(int i=0;i<n;i++) if(bits[i]) s += a[i];
        return s;
    };

    // Build pairs from indices
    auto buildPairs = [&](const vector<int>& idx)->vector<PairEntry>{
        vector<PairEntry> pairs;
        int m = (int)idx.size();
        if (m >= 2) {
            pairs.reserve((size_t)m*(m-1)/2);
            for(int u=0;u<m;u++){
                int iu = idx[u];
                for(int v=u+1;v<m;v++){
                    int iv = idx[v];
                    pairs.push_back({a[iu] + a[iv], iu, iv});
                }
            }
            sort(pairs.begin(), pairs.end());
        }
        return pairs;
    };

    // Build singles sorted
    auto buildSingles = [&](const vector<int>& idx)->vector<pair<ll,int>>{
        vector<pair<ll,int>> s;
        s.reserve(idx.size());
        for(int id: idx) s.emplace_back(a[id], id);
        sort(s.begin(), s.end());
        return s;
    };

    // Local improvement function: returns true if exact reached
    function<bool(vector<char>&, ll&)> local_improve = [&](vector<char>& bits, ll& curSum)->bool {
        int steps = 0;
        while (!time_exceeded()) {
            ll d = T - curSum;
            if (d == 0) return true;
            steps++;
            if (steps > 400) break;

            vector<int> onIdx, offIdx;
            onIdx.reserve(n);
            offIdx.reserve(n);
            for (int i=0;i<n;i++) {
                if (bits[i]) onIdx.push_back(i);
                else offIdx.push_back(i);
            }

            auto onSingles = buildSingles(onIdx);
            auto offSingles = buildSingles(offIdx);
            auto onPairs = buildPairs(onIdx);
            auto offPairs = buildPairs(offIdx);

            ll bestE = llabs(d);
            ll bestDelta = 0;
            vector<int> bestAdd, bestRem;

            auto consider_move = [&](const vector<int>& add, const vector<int>& rem, ll delta){
                ll newE = llabs(d - delta);
                if (newE < bestE) {
                    bestE = newE;
                    bestDelta = delta;
                    bestAdd = add;
                    bestRem = rem;
                }
            };

            // Single flips
            for (auto &pr : offSingles) {
                ll delta = pr.first; // add
                consider_move(vector<int>{pr.second}, vector<int>{}, delta);
            }
            for (auto &pr : onSingles) {
                ll delta = -pr.first; // remove
                consider_move(vector<int>{}, vector<int>{pr.second}, delta);
            }

            // Two additions (off pairs)
            if (!offPairs.empty()) {
                // binary search for nearest to d
                auto it = lower_bound(offPairs.begin(), offPairs.end(), PairEntry{d, -1, -1});
                if (it != offPairs.end()) {
                    consider_move(vector<int>{it->i, it->j}, vector<int>{}, it->sum);
                }
                if (it != offPairs.begin()) {
                    auto it2 = prev(it);
                    consider_move(vector<int>{it2->i, it2->j}, vector<int>{}, it2->sum);
                }
            }
            // Two removals (on pairs)
            if (!onPairs.empty()) {
                // nearest to -d
                ll target = -d;
                auto it = lower_bound(onPairs.begin(), onPairs.end(), PairEntry{target, -1, -1});
                if (it != onPairs.end()) {
                    consider_move(vector<int>{}, vector<int>{it->i, it->j}, -it->sum);
                }
                if (it != onPairs.begin()) {
                    auto it2 = prev(it);
                    consider_move(vector<int>{}, vector<int>{it2->i, it2->j}, -it2->sum);
                }
            }

            // 1+1 (off - on)
            if (!offSingles.empty() && !onSingles.empty()) {
                size_t i = 0, j = 0;
                while (i < offSingles.size() && j < onSingles.size()) {
                    ll diff = offSingles[i].first - onSingles[j].first;
                    consider_move(vector<int>{offSingles[i].second}, vector<int>{onSingles[j].second}, diff);
                    if (diff < d) i++;
                    else j++;
                }
            }

            // 2+1 (offPairs - onSingle)
            if (!offPairs.empty() && !onSingles.empty()) {
                size_t i = 0, j = 0;
                while (i < offPairs.size() && j < onSingles.size()) {
                    ll diff = offPairs[i].sum - onSingles[j].first;
                    consider_move(vector<int>{offPairs[i].i, offPairs[i].j}, vector<int>{onSingles[j].second}, diff);
                    if (diff < d) i++;
                    else j++;
                }
            }

            // 1+2 (offSingle - onPairs)
            if (!offSingles.empty() && !onPairs.empty()) {
                size_t i = 0, j = 0;
                while (i < offSingles.size() && j < onPairs.size()) {
                    ll diff = offSingles[i].first - onPairs[j].sum;
                    consider_move(vector<int>{offSingles[i].second}, vector<int>{onPairs[j].i, onPairs[j].j}, diff);
                    if (diff < d) i++;
                    else j++;
                }
            }

            // 2+2 (offPairs - onPairs)
            if (!offPairs.empty() && !onPairs.empty()) {
                size_t i = 0, j = 0;
                while (i < offPairs.size() && j < onPairs.size()) {
                    ll diff = offPairs[i].sum - onPairs[j].sum;
                    consider_move(vector<int>{offPairs[i].i, offPairs[i].j}, vector<int>{onPairs[j].i, onPairs[j].j}, diff);
                    if (diff < d) i++;
                    else j++;
                }
            }

            if (bestE < llabs(d)) {
                // Apply best move
                for (int idx : bestAdd) bits[idx] = 1;
                for (int idx : bestRem) bits[idx] = 0;
                curSum += bestDelta;
                if (curSum == T) return true;
            } else {
                break;
            }
        }
        return (curSum == T);
    };

    // Meet-in-the-middle exact search on subset of indices (signed values)
    auto mitm_exact = [&](vector<char>& bits, ll& curSum)->bool{
        if (time_exceeded()) return false;
        // Build items: Off -> +a[i]; On -> -a[i]
        struct Item { ll val; int idx; bool wasOn; };
        vector<Item> items;
        items.reserve(n);
        for (int i=0;i<n;i++) {
            if (bits[i]) items.push_back(Item{-a[i], i, true});
            else items.push_back(Item{a[i], i, false});
        }
        // Sort by absolute value desc
        sort(items.begin(), items.end(), [](const Item& L, const Item& R){
            ll al = L.val >= 0 ? L.val : -L.val;
            ll ar = R.val >= 0 ? R.val : -R.val;
            return al > ar;
        });
        int M = (int)items.size();
        int m = min(M, 36); // adjust size for performance
        if (m <= 0) return false;
        items.resize(m);
        int m1 = m / 2;
        int m2 = m - m1;

        vector<ll> v1(m1), v2(m2);
        for (int i=0;i<m1;i++) v1[i] = items[i].val;
        for (int i=0;i<m2;i++) v2[i] = items[m1+i].val;

        int n1 = 1 << m1;
        int n2 = 1 << m2;
        if (time_exceeded()) return false;

        struct SumMask { ll sum; uint32_t mask; };
        vector<SumMask> s1; s1.reserve(n1);
        vector<SumMask> s2; s2.reserve(n2);

        for (int mask=0; mask<n1; mask++) {
            ll s=0;
            for (int j=0;j<m1;j++) if (mask & (1<<j)) s += v1[j];
            s1.push_back({s, (uint32_t)mask});
        }
        for (int mask=0; mask<n2; mask++) {
            ll s=0;
            for (int j=0;j<m2;j++) if (mask & (1<<j)) s += v2[j];
            s2.push_back({s, (uint32_t)mask});
        }

        sort(s2.begin(), s2.end(), [](const SumMask& A, const SumMask& B){ return A.sum < B.sum; });

        ll d = T - curSum;
        for (auto &e1 : s1) {
            if (time_exceeded()) break;
            ll target = d - e1.sum;
            auto range = equal_range(s2.begin(), s2.end(), SumMask{target, 0}, [](const SumMask& A, const SumMask& B){
                return A.sum < B.sum;
            });
            if (range.first != range.second) {
                // Found exact
                uint32_t mask1 = e1.mask;
                uint32_t mask2 = range.first->mask;
                // Apply flips
                for (int j=0;j<m1;j++) if (mask1 & (1u<<j)) {
                    if (items[j].wasOn) bits[items[j].idx] = 0;
                    else bits[items[j].idx] = 1;
                }
                for (int j=0;j<m2;j++) if (mask2 & (1u<<j)) {
                    int idx = m1 + j;
                    if (items[idx].wasOn) bits[items[idx].idx] = 0;
                    else bits[items[idx].idx] = 1;
                }
                curSum = T;
                return true;
            }
        }
        return false;
    };

    // Initializations
    vector<char> bestBits(n, 0);
    ll bestSum = 0;
    ll bestErr = llabs(T - bestSum);

    auto try_attempt = [&](vector<char> bits, ll curSum){
        if (llabs(T - curSum) < bestErr) {
            bestErr = llabs(T - curSum);
            bestBits = bits;
            bestSum = curSum;
        }
        if (time_exceeded()) return;
        bool exact = local_improve(bits, curSum);
        if (llabs(T - curSum) < bestErr) {
            bestErr = llabs(T - curSum);
            bestBits = bits;
            bestSum = curSum;
        }
        if (!exact && !time_exceeded()) {
            bool ok = mitm_exact(bits, curSum);
            if (ok) exact = true;
            if (llabs(T - curSum) < bestErr) {
                bestErr = llabs(T - curSum);
                bestBits = bits;
                bestSum = curSum;
            }
        }
    };

    // Attempt 1: Greedy descending
    {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int i, int j){ return a[i] > a[j]; });
        vector<char> bits(n, 0);
        ll s = 0;
        for (int idx : order) {
            if (s + a[idx] <= T) {
                bits[idx] = 1;
                s += a[idx];
            }
        }
        try_attempt(bits, s);
        if (bestErr == 0) {
            string out(n,'0');
            for (int i=0;i<n;i++) if (bestBits[i]) out[i]='1';
            cout << out;
            return 0;
        }
    }

    // Attempt 2: Randomized probability p = T/sumAll
    {
        double p = (double)T / (double)sumAll;
        if (p < 0) p = 0;
        if (p > 1) p = 1;
        vector<char> bits(n, 0);
        ll s = 0;
        uniform_real_distribution<double> dist(0.0, 1.0);
        for (int i=0;i<n;i++) {
            if (dist(rng) < p) {
                bits[i] = 1; s += a[i];
            }
        }
        try_attempt(bits, s);
        if (bestErr == 0) {
            string out(n,'0');
            for (int i=0;i<n;i++) if (bestBits[i]) out[i]='1';
            cout << out;
            return 0;
        }
    }

    // Attempts 3+: until time limit: mix of random greedy and random 50%
    int attempts = 0;
    while (!time_exceeded()) {
        attempts++;
        // Alternate between random greedy and random Bernoulli
        if (attempts % 2 == 1) {
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);
            vector<char> bits(n, 0);
            ll s = 0;
            for (int idx : order) {
                if (s + a[idx] <= T) {
                    bits[idx] = 1;
                    s += a[idx];
                }
            }
            try_attempt(bits, s);
        } else {
            vector<char> bits(n, 0);
            ll s = 0;
            for (int i=0;i<n;i++) {
                if ((rng() & 1) != 0) {
                    bits[i] = 1;
                    s += a[i];
                }
            }
            try_attempt(bits, s);
        }
        if (bestErr == 0) break;
    }

    string out(n, '0');
    for (int i=0;i<n;i++) if (bestBits[i]) out[i] = '1';
    cout << out;
    return 0;
}